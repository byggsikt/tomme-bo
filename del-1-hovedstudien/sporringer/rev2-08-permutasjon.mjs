// «Tomme bo» — REVISJON 2, steg 8: PERMUTASJONSTESTEN (fagfellens punkt 13 E).
//
// Fagfellen: «ingen av 300 permutasjoner nådde den observerte teststatistikken»
// er en grov fornuftssjekk, men med 300 omstokkinger er den minste direkte
// oppløsbare empiriske halesannsynligheten ca. 1/301 ≈ 0,0033. Den kan ikke
// uavhengig validere en asymptotisk p-verdi nær 7 × 10⁻⁹.
//
// Dette skriptet gjør to ting:
//   (1) utvider permutasjonstesten fra 300 til 100 000 omstokkinger av byggmerket
//       innenfor rettskrets, og
//   (2) sier eksplisitt hva den KAN og IKKE KAN vise. Selv 100 000 omstokkinger
//       har en oppløsningsgrense på 1/(B+1) ≈ 1,0 × 10⁻⁵. Det permutasjonstesten
//       faktisk validerer, er at nullfordelingen til teststatistikken er N(0,1)
//       — og DET er antakelsen den asymptotiske p-verdien hviler på. Derfor
//       rapporteres en full kalibreringsprøve av nullfordelingen
//       (gjennomsnitt, standardavvik, skjevhet, kurtose, Kolmogorov–Smirnov,
//       halefrekvenser) i tillegg til haletellingen.
//
// READ-ONLY. Ingen databasetilgang. Kjøres:
//   node sporringer/rev2-08-permutasjon.mjs

import { lesKohort, logrankStratifisert, grayTest, grayRutenett, rng, normCdf, pTosidigZ,
         kvantil, skrivJson, pst, r1, r2, r3, r4,
         KJORT, KORPUSSLUTT, VINDU } from "./rev2-00-lib.mjs";

const B_LOGRANK = 100000;
const B_GRAY = 20000;
const FRO = 20260830;

const D = lesKohort("sensurert");

// ---------------------------------------------------------------------------
// Observerte statistikker
// ---------------------------------------------------------------------------
const obsLr = logrankStratifisert(D, (r) => r.bygg, (r) => r.tingrett);
const obsGray = grayTest(D.filter((r) => r.bygg), D.filter((r) => !r.bygg));

console.log("«Tomme bo» — revisjon 2, steg 8: permutasjonstesten\n");
console.log(`  observert stratifisert logrank: z = ${r4(obsLr.z)}, HR = ${r3(obsLr.hr)},`
  + ` asymptotisk p = ${obsLr.p.toExponential(3)}`);
console.log(`  observert Grays test:           z = ${r4(obsGray.z)},`
  + ` asymptotisk p = ${obsGray.p.toExponential(3)}\n`);

// ---------------------------------------------------------------------------
// Rask permutasjonsmotor for den stratifiserte logranken
// ---------------------------------------------------------------------------
/**
 * Per stratum forhåndsberegnes: tidene sortert stigende, hvilke indekser som er
 * § 135-hendelser, og bindingsgruppene (like tider). Per omstokking trengs bare
 * (i) en Fisher–Yates-stokking av merkevektoren innenfor stratumet, og
 * (ii) en suffikssum av merket, som gir n1 i hver risikomengde i O(n).
 * Ingen sortering per omstokking.
 */
function byggMotor(data) {
  const per = new Map();
  for (const r of data) {
    if (!per.has(r.tingrett)) per.set(r.tingrett, []);
    per.get(r.tingrett).push(r);
  }
  const strata = [];
  for (const [, rader] of per) {
    const s = rader.slice().sort((a, b) => a.t - b.t);
    const n = s.length;
    const merke = new Uint8Array(n);
    const erHendelse = new Uint8Array(n);
    for (let i = 0; i < n; i++) { merke[i] = s[i].bygg ? 1 : 0; erHendelse[i] = s[i].arsak === 1 ? 1 : 0; }
    // bindingsgrupper med minst én hendelse
    const grupper = [];
    let i = 0;
    while (i < n) {
      let j = i;
      while (j < n && s[j].t === s[i].t) j++;
      let d = 0;
      const hendIdx = [];
      for (let k = i; k < j; k++) if (erHendelse[k]) { d++; hendIdx.push(k); }
      if (d > 0) grupper.push({ start: i, d, hendIdx: Int32Array.from(hendIdx) });
      i = j;
    }
    strata.push({ n, merke, grupper, cum1: new Int32Array(n + 1) });
  }
  return strata;
}

/** Beregner den stratifiserte logrank-z for gjeldende merkevektorer. */
function logrankZ(strata) {
  let OE = 0, V = 0;
  for (const s of strata) {
    const { n, merke, grupper, cum1 } = s;
    cum1[n] = 0;
    for (let i = n - 1; i >= 0; i--) cum1[i] = cum1[i + 1] + merke[i];
    for (const g of grupper) {
      const nAtt = n - g.start;
      const n1 = cum1[g.start];
      if (nAtt <= 1 || n1 === 0 || n1 === nAtt) continue;
      let d1 = 0;
      for (let k = 0; k < g.hendIdx.length; k++) d1 += merke[g.hendIdx[k]];
      const f = n1 / nAtt;
      OE += d1 - g.d * f;
      V += (g.d * f * (1 - f) * (nAtt - g.d)) / (nAtt - 1);
    }
  }
  return OE / Math.sqrt(V);
}

const motor = byggMotor(D);
const zKontroll = logrankZ(motor);
console.log(`  motorkontroll: z = ${r4(zKontroll)} mot bibliotekets ${r4(obsLr.z)}`
  + `  → differanse ${(Math.abs(zKontroll - obsLr.z)).toExponential(2)}`);
if (Math.abs(zKontroll - obsLr.z) > 1e-9) {
  console.error("STOPP: permutasjonsmotoren reproduserer ikke bibliotekets teststatistikk.");
  process.exit(1);
}

// ---------------------------------------------------------------------------
// Permutasjon: stokk byggmerket INNENFOR hver rettskrets
// ---------------------------------------------------------------------------
const rnd = rng(FRO);
const zPerm = new Float64Array(B_LOGRANK);
const t0 = Date.now();
for (let b = 0; b < B_LOGRANK; b++) {
  for (const s of motor) {
    const m = s.merke;
    for (let i = s.n - 1; i > 0; i--) {
      const j = (rnd() * (i + 1)) | 0;
      const tmp = m[i]; m[i] = m[j]; m[j] = tmp;
    }
  }
  zPerm[b] = logrankZ(motor);
}
const sek = (Date.now() - t0) / 1000;
console.log(`\n  ${B_LOGRANK.toLocaleString("nb-NO")} omstokkinger på ${r1(sek)} s`);

// ---------------------------------------------------------------------------
// Haletelling og kalibrering av nullfordelingen
// ---------------------------------------------------------------------------
const aObs = Math.abs(obsLr.z);
let ekstremer = 0, maksAbs = 0;
for (let b = 0; b < B_LOGRANK; b++) {
  const a = Math.abs(zPerm[b]);
  if (a >= aObs) ekstremer++;
  if (a > maksAbs) maksAbs = a;
}
const pPerm = (1 + ekstremer) / (B_LOGRANK + 1);
const oppløsning = 1 / (B_LOGRANK + 1);

const arr = Array.from(zPerm);
const snitt = arr.reduce((a, b) => a + b, 0) / arr.length;
const sd = Math.sqrt(arr.reduce((a, b) => a + (b - snitt) ** 2, 0) / (arr.length - 1));
const m3 = arr.reduce((a, b) => a + ((b - snitt) / sd) ** 3, 0) / arr.length;
const m4 = arr.reduce((a, b) => a + ((b - snitt) / sd) ** 4, 0) / arr.length;
const sortert = arr.slice().sort((a, b) => a - b);
// Kolmogorov–Smirnov mot N(0,1)
let ks = 0;
for (let i = 0; i < sortert.length; i++) {
  const F = normCdf(sortert[i]);
  ks = Math.max(ks, Math.abs((i + 1) / sortert.length - F), Math.abs(F - i / sortert.length));
}
const ksStat = ks * Math.sqrt(sortert.length);
// asymptotisk KS-p (Kolmogorovs fordeling)
const ksP = (() => { let s = 0; for (let k = 1; k <= 100; k++) s += Math.pow(-1, k - 1) * Math.exp(-2 * k * k * ksStat * ksStat); return Math.min(1, 2 * s); })();

const haler = [1.959963984540054, 2.5758293035489, 3.2905267314919, 4].map((c) => ({
  grense: r4(c),
  forventet_pst: pst(2 * (1 - normCdf(c)), 4),
  observert_pst: pst(arr.filter((z) => Math.abs(z) >= c).length / arr.length, 4),
  antall: arr.filter((z) => Math.abs(z) >= c).length,
}));

console.log("\n  HALETELLING");
console.log(`    omstokkinger med |z| ≥ |z_obs| = ${r3(aObs)}: ${ekstremer}`);
console.log(`    permutasjons-p = (1 + ${ekstremer})/(${B_LOGRANK} + 1) = ${pPerm.toExponential(3)}`);
console.log(`    OPPLØSNINGSGRENSE 1/(B+1) = ${oppløsning.toExponential(3)}`);
console.log(`    største |z| i nullfordelingen: ${r3(maksAbs)}`);
console.log(`    den asymptotiske p-verdien ${obsLr.p.toExponential(2)} ligger`
  + ` ${r1(Math.log10(oppløsning / obsLr.p))} tierpotenser under oppløsningsgrensen —`
  + " permutasjonstesten kan derfor IKKE bekrefte den direkte.");

console.log("\n  KALIBRERING AV NULLFORDELINGEN (det permutasjonstesten faktisk validerer)");
console.log(`    gjennomsnitt ${r4(snitt)} (forventet 0), standardavvik ${r4(sd)} (forventet 1)`);
console.log(`    skjevhet ${r4(m3)} (forventet 0), kurtose ${r4(m4)} (forventet 3)`);
console.log(`    Kolmogorov–Smirnov mot N(0,1): D√B = ${r3(ksStat)}, p = ${r3(ksP)}`);
for (const h of haler)
  console.log(`    |z| ≥ ${h.grense}: observert ${h.observert_pst} % mot forventet ${h.forventet_pst} %`
    + ` (${h.antall} av ${B_LOGRANK})`);

// ---------------------------------------------------------------------------
// Grays test, permutert ustratifisert
// ---------------------------------------------------------------------------
console.log(`\n  GRAYS TEST — ${B_GRAY.toLocaleString("nb-NO")} ustratifiserte omstokkinger`);
const rnd2 = rng(FRO + 7);
const rut = grayRutenett(D);
const merkeG = D.map((r) => (r.bygg ? 1 : 0));
const zG = new Float64Array(B_GRAY);
const t1 = Date.now();
for (let b = 0; b < B_GRAY; b++) {
  for (let i = merkeG.length - 1; i > 0; i--) {
    const j = (rnd2() * (i + 1)) | 0;
    const tmp = merkeG[i]; merkeG[i] = merkeG[j]; merkeG[j] = tmp;
  }
  const g1 = [], g2 = [];
  for (let i = 0; i < D.length; i++) (merkeG[i] ? g1 : g2).push(D[i]);
  zG[b] = grayTest(g1, g2, rut).z;
}
const gArr = Array.from(zG);
const gSnitt = gArr.reduce((a, b) => a + b, 0) / gArr.length;
const gSd = Math.sqrt(gArr.reduce((a, b) => a + (b - gSnitt) ** 2, 0) / (gArr.length - 1));
const gEkstremer = gArr.filter((z) => Math.abs(z) >= Math.abs(obsGray.z)).length;
console.log(`    ${r1((Date.now() - t1) / 1000)} s. gjennomsnitt ${r4(gSnitt)}, standardavvik ${r4(gSd)}`);
console.log(`    |z| ≥ |z_obs| = ${r3(Math.abs(obsGray.z))}: ${gEkstremer};`
  + ` permutasjons-p = ${((1 + gEkstremer) / (B_GRAY + 1)).toExponential(3)}`
  + ` (oppløsningsgrense ${(1 / (B_GRAY + 1)).toExponential(2)})`);

const ut = {
  studie: "Tomme bo — revisjon 2 etter fagfellevurdering",
  leverer: "fagfellens punkt 13 E — permutasjonstesten utvidet og dens oppløsningsgrense dokumentert",
  skript: "sporringer/rev2-08-permutasjon.mjs",
  kjort: KJORT,
  datagrunnlag: "offentlig tilgjengelige registerkunngjøringer om konkursbehandling",
  frosset_uttrekk: "data/_kohort-rader-arbeidskopi.json",
  kohortvindu: VINDU, sensureringsdato: KORPUSSLUTT,
  generator: { type: "mulberry32", fro: FRO, stokking: "Fisher–Yates" },

  stratifisert_logrank: {
    observert: { z: r4(obsLr.z), hr: r4(obsLr.hr), OE: r2(obsLr.OE), V: r2(obsLr.V),
      asymptotisk_p: obsLr.p, strata: obsLr.strata },
    permutasjon: {
      omstokkinger: B_LOGRANK,
      stokking: "byggmerket omstokket INNENFOR hver rettskrets; antallet byggbo per krets er bevart",
      antall_minst_saa_ekstreme: ekstremer,
      permutasjons_p: pPerm,
      oppløsningsgrense_1_over_B_pluss_1: oppløsning,
      storste_abs_z_i_nullfordelingen: r3(maksAbs),
      tierpotenser_mellom_oppløsning_og_asymptotisk_p: r1(Math.log10(oppløsning / obsLr.p)),
    },
    kalibrering_av_nullfordelingen: {
      gjennomsnitt: r4(snitt), forventet_gjennomsnitt: 0,
      standardavvik: r4(sd), forventet_standardavvik: 1,
      skjevhet: r4(m3), forventet_skjevhet: 0,
      kurtose: r4(m4), forventet_kurtose: 3,
      kolmogorov_smirnov: { statistikk_D_gange_rot_B: r3(ksStat), p: r3(ksP) },
      halefrekvenser: haler,
      persentiler: { p1: r3(kvantil(sortert, 0.01)), p5: r3(kvantil(sortert, 0.05)),
        p25: r3(kvantil(sortert, 0.25)), p50: r3(kvantil(sortert, 0.5)),
        p75: r3(kvantil(sortert, 0.75)), p95: r3(kvantil(sortert, 0.95)),
        p99: r3(kvantil(sortert, 0.99)) },
    },
  },

  grays_test: {
    observert: { z: r4(obsGray.z), asymptotisk_p: obsGray.p },
    permutasjon: { omstokkinger: B_GRAY, stokking: "byggmerket omstokket ustratifisert",
      antall_minst_saa_ekstreme: gEkstremer,
      permutasjons_p: (1 + gEkstremer) / (B_GRAY + 1),
      oppløsningsgrense: 1 / (B_GRAY + 1),
      nullfordeling: { gjennomsnitt: r4(gSnitt), standardavvik: r4(gSd) } },
  },

  paakrevd_formulering: "Teststatistikken er permutasjonsvalidert med " + B_LOGRANK.toLocaleString("nb-NO")
    + " omstokkinger av byggmerket innenfor hver rettskrets. Ingen omstokking nådde den observerte "
    + "verdien. Den minste halesannsynligheten en permutasjonstest med B omstokkinger kan oppløse, "
    + "er 1/(B + 1) — her " + oppløsning.toExponential(1) + " — så testen kan ikke bekrefte en "
    + "asymptotisk p-verdi på " + obsLr.p.toExponential(1) + " direkte. Det den viser, er at "
    + "nullfordelingen til teststatistikken er standard normalfordelt (gjennomsnitt " + r4(snitt)
    + ", standardavvik " + r4(sd) + ", Kolmogorov–Smirnov p = " + r3(ksP) + "), og det er nettopp "
    + "den antakelsen den asymptotiske p-verdien hviler på.",

  forbudt_formulering: "«Permutasjonstesten validerer p ≈ 7 × 10⁻⁹.» En permutasjonstest med B "
    + "omstokkinger kan aldri oppløse en halesannsynlighet under 1/(B + 1).",
};
skrivJson(`data/rev2-08-permutasjon-${KJORT}.json`, ut);
