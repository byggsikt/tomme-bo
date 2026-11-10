// «Tomme bo» — REVISJON 2, steg 6: DOMSTOLSKONTRASTER (fagfellens punkt 13 A/B/D).
//
// Fagfellen: «bare 5 av 120 par har ikke-overlappende KI» er deskriptivt nyttig,
// men er ikke 120 formelle tester. Vil manuskriptet si at én krets skiller seg,
// trengs formelle parvise kontraster med multiplisitetskorreksjon (Holm) eller en
// hierarkisk modell. Og domstolenes varighetstall bygger på fullførte saker, som
// påvirkes av ulik sensureringsgrad — de bør bruke en sensureringsbevisst estimator.
//
// Leverer:
//   (a) reproduksjon av homogenitetstesten og av «5 av 120 ikke-overlappende KI»;
//   (b) 120 parvise Fisher-eksakte kontraster med Holm-korreksjon;
//   (c) 16 «én krets mot resten»-kontraster med Holm-korreksjon;
//   (d) en hierarkisk logistisk-normal modell (random effects) med ML via
//       Gauss–Hermite-kvadratur, LRT for τ = 0, og empirisk-Bayes-krympede
//       kretsestimater med 95 % troverdighetsintervall;
//   (e) SENSURERINGSBEVISST varighet per krets: 24-måneders kumulativ insidens
//       og CIF-median, som erstatter medianen blant fullførte saker.
//
// Minstecelleregel: kun kretser med n ≥ 100 publiseres per krets (alle celler
// ≥ 10). Den hierarkiske modellen kjøres i tillegg på alle 23 kretser, men da
// rapporteres bare aggregatene (μ, τ), ikke kretsvise tall.
//
// READ-ONLY. Ingen databasetilgang. Kjøres:
//   node sporringer/rev2-06-domstolskontraster.mjs

import { lesKohort, aalenJohansen, ajF, ajKI, ajKvantil, risikoVed, clopperPearson,
         wilson, fisherEksakt, holm, pKhi, normCdf,
         skrivJson, pst, r1, r2, r3, r4, KJORT, KORPUSSLUTT, VINDU, H24 } from "./rev2-00-lib.mjs";

const D = lesKohort("tidligst"); // kanonisk telling av utfall
const MINN = 100;

const perKrets = new Map();
for (const r of D) {
  if (!perKrets.has(r.tingrett)) perKrets.set(r.tingrett, []);
  perKrets.get(r.tingrett).push(r);
}
const alle23 = [...perKrets.entries()].map(([krets, rader]) => ({
  krets, n: rader.length, k: rader.filter((r) => r.innstilt).length, rader }));
const pub = alle23.filter((c) => c.n >= MINN).sort((a, b) => a.k / a.n - b.k / b.n);

console.log("«Tomme bo» — revisjon 2, steg 6: domstolskontraster\n");
console.log(`  ${pub.length} kretser med n ≥ ${MINN}, til sammen ${pub.reduce((s, c) => s + c.n, 0)}`
  + ` av ${D.length} saker (${pst(pub.reduce((s, c) => s + c.n, 0) / D.length, 1)} %)`);
console.log(`  minste celle blant de publiserte: ${Math.min(...pub.map((c) => Math.min(c.k, c.n - c.k)))}`);

// ---------------------------------------------------------------------------
// (a) homogenitet og «5 av 120»
// ---------------------------------------------------------------------------
const Ntot = pub.reduce((s, c) => s + c.n, 0), Ktot = pub.reduce((s, c) => s + c.k, 0);
const pAll = Ktot / Ntot;
let khi = 0;
for (const c of pub) khi += Math.pow(c.k - c.n * pAll, 2) / (c.n * pAll * (1 - pAll));
const dfHom = pub.length - 1;

for (const c of pub) {
  [c.cpLav, c.cpHoy] = clopperPearson(c.k, c.n);
  [c.wLav, c.wHoy] = wilson(c.k, c.n);
  c.andel = c.k / c.n;
}
let ikkeOverlappCP = 0, ikkeOverlappW = 0;
const overlappPar = [];
for (let i = 0; i < pub.length; i++) for (let j = i + 1; j < pub.length; j++) {
  const a = pub[i], b = pub[j];
  const cp = a.cpHoy < b.cpLav || b.cpHoy < a.cpLav;
  const w = a.wHoy < b.wLav || b.wHoy < a.wLav;
  if (cp) { ikkeOverlappCP++; overlappPar.push({ a: a.krets, b: b.krets, type: "Clopper–Pearson" }); }
  if (w) ikkeOverlappW++;
}
console.log(`\n(a) HOMOGENITET: χ² = ${r1(khi)}, df = ${dfHom}, p = ${pKhi(khi, dfHom).toExponential(2)}`);
console.log(`    ikke-overlappende 95 %-KI: ${ikkeOverlappCP} av ${(pub.length * (pub.length - 1)) / 2} par`
  + ` (Clopper–Pearson); ${ikkeOverlappW} par med Wilson-intervall`);
console.log("    MERK: dette er en DESKRIPTIV telling, ikke 120 formelle tester.");

// ---------------------------------------------------------------------------
// (b) 120 parvise Fisher-kontraster med Holm
// ---------------------------------------------------------------------------
const par = [];
for (let i = 0; i < pub.length; i++) for (let j = i + 1; j < pub.length; j++) {
  const a = pub[i], b = pub[j];
  par.push({ krets_a: a.krets, krets_b: b.krets,
    andel_a_pst: pst(a.andel, 1), andel_b_pst: pst(b.andel, 1),
    differanse_pp: pst(a.andel - b.andel, 1),
    p_ra: fisherEksakt(a.k, a.n - a.k, b.k, b.n - b.k) });
}
const pHolm = holm(par.map((p) => p.p_ra));
par.forEach((p, i) => { p.p_holm = pHolm[i]; });
const signPar = par.filter((p) => p.p_holm < 0.05).sort((x, y) => x.p_holm - y.p_holm);
const signRa = par.filter((p) => p.p_ra < 0.05);

console.log(`\n(b) 120 PARVISE FISHER-KONTRASTER`);
console.log(`    ${signRa.length} av ${par.length} par har ukorrigert p < 0,05`);
console.log(`    ${signPar.length} av ${par.length} par overlever Holm-korreksjon på 5 %-nivå:`);
for (const p of signPar)
  console.log(`      ${p.krets_a} (${p.andel_a_pst} %) mot ${p.krets_b} (${p.andel_b_pst} %):`
    + ` ${p.differanse_pp} pp, p_rå = ${p.p_ra.toExponential(2)}, p_Holm = ${r4(p.p_holm)}`);

// ---------------------------------------------------------------------------
// (c) én krets mot resten, Holm-korrigert
// ---------------------------------------------------------------------------
const motResten = pub.map((c) => {
  const kR = Ktot - c.k, nR = Ntot - c.n;
  return { krets: c.krets, n: c.n, andel_pst: pst(c.andel, 1),
    resten_andel_pst: pst(kR / nR, 1), differanse_pp: pst(c.andel - kR / nR, 1),
    p_ra: fisherEksakt(c.k, c.n - c.k, kR, nR - kR) };
});
const hR = holm(motResten.map((m) => m.p_ra));
motResten.forEach((m, i) => { m.p_holm = hR[i]; });
console.log("\n(c) ÉN KRETS MOT RESTEN (16 tester, Holm-korrigert)");
for (const m of motResten.slice().sort((a, b) => a.p_holm - b.p_holm).filter((m) => m.p_holm < 0.2))
  console.log(`    ${m.krets.padEnd(38)} ${String(m.andel_pst).padStart(5)} % mot ${m.resten_andel_pst} %`
    + `  (${m.differanse_pp} pp)  p_rå = ${m.p_ra.toExponential(2)}, p_Holm = ${r4(m.p_holm)}`
    + (m.p_holm < 0.05 ? "   ← skiller seg" : ""));

// ---------------------------------------------------------------------------
// (d) hierarkisk logistisk-normal modell
// ---------------------------------------------------------------------------
/** Gauss–Hermite-noder og -vekter (Numerical Recipes gauher). */
function gaussHermite(n) {
  const EPS = 1e-14, PIM4 = 0.7511255444649425, MAXIT = 200;
  const x = new Array(n), w = new Array(n), m = Math.floor((n + 1) / 2);
  let z = 0, pp = 0;
  for (let i = 0; i < m; i++) {
    if (i === 0) z = Math.sqrt(2 * n + 1) - 1.85575 * Math.pow(2 * n + 1, -1 / 6);
    else if (i === 1) z -= (1.14 * Math.pow(n, 0.426)) / z;
    else if (i === 2) z = 1.86 * z - 0.86 * x[0];
    else if (i === 3) z = 1.91 * z - 0.91 * x[1];
    else z = 2 * z - x[i - 2];
    for (let it = 0; it < MAXIT; it++) {
      let p1 = PIM4, p2 = 0;
      for (let j = 0; j < n; j++) {
        const p3 = p2; p2 = p1;
        p1 = z * Math.sqrt(2 / (j + 1)) * p2 - Math.sqrt(j / (j + 1)) * p3;
      }
      pp = Math.sqrt(2 * n) * p2;
      const z1 = z; z = z1 - p1 / pp;
      if (Math.abs(z - z1) <= EPS) break;
    }
    x[i] = z; x[n - 1 - i] = -z; w[i] = 2 / (pp * pp); w[n - 1 - i] = w[i];
  }
  return { x, w };
}
const GH = gaussHermite(60);
const SQPI = Math.sqrt(Math.PI);
const expit = (u) => 1 / (1 + Math.exp(-u));

/** log Σ_j (w_j/√π) · Binom(k; n, expit(μ + τ√2 z_j))  — stabil logsumexp. */
function logLikKrets(k, n, mu, tau) {
  const ledd = new Array(GH.x.length);
  for (let j = 0; j < GH.x.length; j++) {
    const p = expit(mu + tau * Math.SQRT2 * GH.x[j]);
    const lp = p <= 0 ? (k > 0 ? -Infinity : 0) : p >= 1 ? (k < n ? -Infinity : 0)
      : k * Math.log(p) + (n - k) * Math.log(1 - p);
    ledd[j] = Math.log(GH.w[j] / SQPI) + lp;
  }
  const mx = Math.max(...ledd);
  if (!Number.isFinite(mx)) return -Infinity;
  return mx + Math.log(ledd.reduce((s, v) => s + Math.exp(v - mx), 0));
}
const logLik = (kretser, mu, tau) =>
  kretser.reduce((s, c) => s + logLikKrets(c.k, c.n, mu, tau), 0);

/** ML ved nøstet søk: grovt rutenett → gyllent snitt i hver retning. */
function tilpass(kretser) {
  let beste = { ll: -Infinity, mu: 0, tau: 0 };
  for (let mu = 0.5; mu <= 2.0; mu += 0.01)
    for (let tau = 0; tau <= 0.6; tau += 0.005) {
      const ll = logLik(kretser, mu, tau);
      if (ll > beste.ll) beste = { ll, mu, tau };
    }
  for (let runde = 0; runde < 6; runde++) {
    const dm = 0.01 / Math.pow(3, runde), dt = 0.005 / Math.pow(3, runde);
    for (let a = -3; a <= 3; a++) for (let b = -3; b <= 3; b++) {
      const mu = beste.mu + a * dm, tau = Math.max(0, beste.tau + b * dt);
      const ll = logLik(kretser, mu, tau);
      if (ll > beste.ll) beste = { ll, mu, tau };
    }
  }
  // nullmodell τ = 0: ren binomisk, μ̂ = logit(Σk/Σn)
  const K = kretser.reduce((s, c) => s + c.k, 0), N = kretser.reduce((s, c) => s + c.n, 0);
  const mu0 = Math.log(K / (N - K));
  const ll0 = logLik(kretser, mu0, 0);
  const lrt = 2 * (beste.ll - ll0);
  return { ...beste, mu0, ll0, lrt,
    // grensetest: 0,5·χ²(0) + 0,5·χ²(1)
    p_lrt: 0.5 * pKhi(Math.max(0, lrt), 1) };
}

/** Empirisk Bayes: posteriorfordeling for kretsens egen andel. */
function posterior(k, n, mu, tau) {
  const G = 4001, lo = -6, hi = 6, h = (hi - lo) / (G - 1);
  const b = new Array(G), lw = new Array(G);
  for (let i = 0; i < G; i++) {
    b[i] = lo + i * h;
    const p = expit(mu + tau * b[i]);
    lw[i] = -0.5 * b[i] * b[i] + k * Math.log(p) + (n - k) * Math.log(1 - p);
  }
  const mx = Math.max(...lw);
  const w = lw.map((v) => Math.exp(v - mx));
  const S = w.reduce((a, v) => a + v, 0);
  const p = b.map((bi) => expit(mu + tau * bi));
  const mean = p.reduce((a, pi, i) => a + pi * w[i], 0) / S;
  // kvantiler på p (p er monotont voksende i b)
  let cum = 0; let q025 = null, q975 = null, q50 = null;
  for (let i = 0; i < G; i++) {
    cum += w[i] / S;
    if (q025 === null && cum >= 0.025) q025 = p[i];
    if (q50 === null && cum >= 0.5) q50 = p[i];
    if (q975 === null && cum >= 0.975) { q975 = p[i]; break; }
  }
  // posterior sannsynlighet for at kretsen ligger under/over totalgjennomsnittet
  const pTot = expit(mu);
  let under = 0;
  for (let i = 0; i < G; i++) if (p[i] < pTot) under += w[i] / S;
  return { mean, q025, q50, q975, p_under_snittet: under };
}

const fit16 = tilpass(pub);
const fit23 = tilpass(alle23);
console.log("\n(d) HIERARKISK LOGISTISK-NORMAL MODELL (random effects, ML via Gauss–Hermite)");
console.log(`    16 kretser (n ≥ 100): μ̂ = ${r4(fit16.mu)} (andel ${pst(expit(fit16.mu), 2)} %),`
  + ` τ̂ = ${r4(fit16.tau)} på logit-skala`);
console.log(`      LRT mot τ = 0: ${r3(fit16.lrt)}, p = ${fit16.p_lrt.toExponential(2)}`
  + ` (0,5·χ²(0) + 0,5·χ²(1), grensetest)`);
console.log(`      implisert spenn ±2τ: ${pst(expit(fit16.mu - 2 * fit16.tau), 1)}`
  + `–${pst(expit(fit16.mu + 2 * fit16.tau), 1)} %`);
console.log(`    alle 23 kretser:     μ̂ = ${r4(fit23.mu)}, τ̂ = ${r4(fit23.tau)},`
  + ` LRT = ${r3(fit23.lrt)}, p = ${fit23.p_lrt.toExponential(2)}`);

const krympet = pub.map((c) => {
  const po = posterior(c.k, c.n, fit16.mu, fit16.tau);
  return { krets: c.krets, saker: c.n, innstilt: c.k,
    raa_andel_pst: pst(c.andel, 1), raa_cp95_pst: [pst(c.cpLav, 1), pst(c.cpHoy, 1)],
    krympet_andel_pst: pst(po.mean, 1),
    krympet_95_pst: [pst(po.q025, 1), pst(po.q975, 1)],
    krymping_pp: pst(po.mean - c.andel, 2),
    post_sanns_under_snittet: r3(po.p_under_snittet) };
});
console.log("\n    krympede kretsestimater (empirisk Bayes):");
for (const k of krympet)
  console.log(`      ${k.krets.padEnd(38)} rå ${String(k.raa_andel_pst).padStart(5)} %`
    + ` [${k.raa_cp95_pst.join("–")}]  →  krympet ${String(k.krympet_andel_pst).padStart(5)} %`
    + ` [${k.krympet_95_pst.join("–")}]  P(under snittet) = ${k.post_sanns_under_snittet}`);

// ---------------------------------------------------------------------------
// (e) sensureringsbevisst varighet per krets
// ---------------------------------------------------------------------------
const varighet = pub.map((c) => {
  const aj = aalenJohansen(c.rader);
  const [lo, hi] = ajKI(aj, H24, "loglog");
  const raa = c.rader.filter((r) => r.arsak === 1).map((r) => r.t).sort((a, b) => a - b);
  const med = raa.length ? (raa.length % 2 ? raa[(raa.length - 1) / 2]
    : (raa[raa.length / 2 - 1] + raa[raa.length / 2]) / 2) : null;
  return { krets: c.krets, saker: c.n,
    cif24_pst: pst(ajF(aj, H24), 1), cif24_ki95_pst: [pst(lo, 1), pst(hi, 1)],
    cif_median_dager: ajKvantil(aj, 0.5),
    raa_median_fullforte_dager: med,
    risikomengde_730d: risikoVed(c.rader, H24),
    andel_uavgjorte_pst: pst(c.rader.filter((r) => r.utfall === "fortsatt_apen").length / c.n, 1) };
});
const cifSort = varighet.slice().sort((a, b) => a.cif_median_dager - b.cif_median_dager);
const raaSort = varighet.slice().sort((a, b) => a.raa_median_fullforte_dager - b.raa_median_fullforte_dager);
console.log("\n(e) SENSURERINGSBEVISST VARIGHET PER KRETS (kumulativ insidens)");
console.log(`    CIF-median spenn:            ${cifSort[0].cif_median_dager} (${cifSort[0].krets})`
  + ` – ${cifSort[cifSort.length - 1].cif_median_dager} (${cifSort[cifSort.length - 1].krets})`);
console.log(`    rå median (fullførte) spenn: ${raaSort[0].raa_median_fullforte_dager} (${raaSort[0].krets})`
  + ` – ${raaSort[raaSort.length - 1].raa_median_fullforte_dager} (${raaSort[raaSort.length - 1].krets})`);
console.log(`    24-mnd CIF spenn:            ${Math.min(...varighet.map((v) => v.cif24_pst))}`
  + `–${Math.max(...varighet.map((v) => v.cif24_pst))} %`);

const ut = {
  studie: "Tomme bo — revisjon 2 etter fagfellevurdering",
  leverer: "fagfellens punkt 13 A/B/D — formelle, multiplisitetskorrigerte domstolskontraster "
    + "og en sensureringsbevisst varighetssammenlikning",
  skript: "sporringer/rev2-06-domstolskontraster.mjs",
  kjort: KJORT,
  datagrunnlag: "offentlig tilgjengelige registerkunngjøringer om konkursbehandling",
  frosset_uttrekk: "data/_kohort-rader-arbeidskopi.json",
  kohortvindu: VINDU, sensureringsdato: KORPUSSLUTT,
  publiseringsregel: `kun kretser med n ≥ ${MINN}; minste publiserte celle `
    + Math.min(...pub.map((c) => Math.min(c.k, c.n - c.k))),
  omfang: { kretser_publisert: pub.length, kretser_totalt: alle23.length,
    saker_publisert: Ntot, saker_totalt: D.length, dekning_pst: pst(Ntot / D.length, 1) },

  a_deskriptivt: {
    homogenitetstest: { khikvadrat: r1(khi), df: dfHom, p: pKhi(khi, dfHom) },
    ikke_overlappende_ki: { clopper_pearson: ikkeOverlappCP, wilson: ikkeOverlappW,
      antall_par: (pub.length * (pub.length - 1)) / 2,
      par: overlappPar,
      advarsel: "En telling av ikke-overlappende marginale konfidensintervaller er IKKE 120 "
        + "formelle parvise tester og skal ikke omtales som signifikans." },
  },

  b_parvise_holm: {
    metode: "Fishers eksakte tosidige test på hvert av de 120 parene, deretter Holm–Bonferroni "
      + "over alle 120 p-verdier.",
    antall_par: par.length,
    signifikante_ukorrigert: signRa.length,
    signifikante_etter_holm: signPar.length,
    overlevende_par: signPar,
    alle_par: par.map((p) => ({ ...p, p_ra: p.p_ra, p_holm: p.p_holm })),
  },

  c_en_krets_mot_resten: {
    metode: "16 Fisher-eksakte tester, hver krets mot summen av de øvrige 15, Holm-korrigert.",
    tester: motResten.slice().sort((a, b) => a.p_holm - b.p_holm),
    skiller_seg_etter_holm: motResten.filter((m) => m.p_holm < 0.05).map((m) => m.krets),
  },

  d_hierarkisk_modell: {
    modell: "k_i ~ Binom(n_i, expit(μ + b_i)), b_i ~ N(0, τ²). ML ved 60-punkts "
      + "Gauss–Hermite-kvadratur; nøstet rutenettsøk med seks forfiningsrunder.",
    tilpasning_16_kretser: { mu: r4(fit16.mu), tau: r4(fit16.tau),
      andel_ved_mu_pst: pst(expit(fit16.mu), 2), loglik: r3(fit16.ll),
      loglik_null: r3(fit16.ll0), lrt: r3(fit16.lrt), p_lrt: fit16.p_lrt,
      lrt_referansefordeling: "0,5·χ²(0) + 0,5·χ²(1) — τ = 0 ligger på parameterrommets rand",
      implisert_spenn_2tau_pst: [pst(expit(fit16.mu - 2 * fit16.tau), 1),
        pst(expit(fit16.mu + 2 * fit16.tau), 1)] },
    tilpasning_23_kretser: { mu: r4(fit23.mu), tau: r4(fit23.tau), lrt: r3(fit23.lrt),
      p_lrt: fit23.p_lrt,
      merknad: "Kretsvise tall publiseres ikke for de sju små kretsene (minstecelleregelen)." },
    krympede_kretsestimater: krympet,
    tolkning: "Variasjonen mellom kretsene er reell (τ̂ > 0 med LRT-belegg), men den krympede "
      + "modellen viser hvor lite av spennet som overlever: rangeringen mellom nabokretser er "
      + "ikke identifisert, og kun kretser hvis krympede intervall ligger klart utenfor μ̂ kan "
      + "omtales som avvikende.",
  },

  e_sensureringsbevisst_varighet: {
    begrunnelse: "Medianen blant fullførte saker påvirkes av at kretsene har ulik andel uavgjorte bo. "
      + "Kumulativ insidens bruker hele kretsens kohort.",
    per_krets: varighet,
    spenn: {
      cif_median_dager: [cifSort[0].cif_median_dager, cifSort[cifSort.length - 1].cif_median_dager],
      cif_median_kretser: [cifSort[0].krets, cifSort[cifSort.length - 1].krets],
      raa_median_dager: [raaSort[0].raa_median_fullforte_dager,
        raaSort[raaSort.length - 1].raa_median_fullforte_dager],
      raa_median_kretser: [raaSort[0].krets, raaSort[raaSort.length - 1].krets],
      cif24_pst: [Math.min(...varighet.map((v) => v.cif24_pst)), Math.max(...varighet.map((v) => v.cif24_pst))],
    },
  },
};
skrivJson(`data/rev2-06-domstolskontraster-${KJORT}.json`, ut);
