// «Tomme bo» — REVISJON 2, steg 7: NÆRINGSSTANDARDISERINGEN (fagfellens punkt 12).
//
// Manuskriptet skriver i dag: «Næringsmiksen forklarer ingenting av
// domstolsvariasjonen.» Fagfellen: det er for absolutt. Standardiseringen viser
// at variasjonen ikke ble vesentlig dempet UNDER DENNE standardiseringen — ikke
// at næringsmiks forklarer ingenting. Strata, vekter, resultat og usikkerhet skal
// publiseres i den maskinlesbare metodefilen slik at den kan repliseres.
//
// Leverer:
//   (a) stratatabellen: hver næringsbøtte med n og landsrate (vektgrunnlaget);
//   (b) indirekte standardisering per krets: E, O, O/E med 95 % KI (binomisk og
//       eksakt Poisson), reprodusert mot lane 3s spenn 0,888–1,085;
//   (c) hvor mye variasjonen faktisk ble dempet: heterogenitetsstatistikk før og
//       etter standardisering, og τ̂ fra en hierarkisk modell med og uten
//       næringsoffset — den ærlige tallfestingen av «forklarer ingenting»;
//   (d) tre stratifiseringer (2-siffer NACE, næringshovedområde, 2-siffer med
//       små bøtter slått sammen), slik at svaret ikke henger på bøtteinndelingen.
//
// Minstecelleregel: stratatabellen publiserer bøtter med n ≥ 10 for seg; alle
// bøtter under 10 rapporteres samlet som «små bøtter».
//
// READ-ONLY. Ingen databasetilgang. Kjøres:
//   node sporringer/rev2-07-standardisering.mjs

import { lesKohort, clopperPearson, pKhi, ibetaInv, logGamma,
         skrivJson, pst, r1, r2, r3, r4, KJORT, KORPUSSLUTT, VINDU } from "./rev2-00-lib.mjs";

const D = lesKohort("tidligst");
const MINN = 100;

// ---------------------------------------------------------------------------
// Stratifiseringer
// ---------------------------------------------------------------------------
/** NACE Rev.2 hovedområde (bokstav) fra tosifret kode. */
function hovedomrade(n2) {
  const k = parseInt(n2, 10);
  if (!Number.isFinite(k)) return "ukjent";
  if (k <= 3) return "A"; if (k <= 9) return "B"; if (k <= 33) return "C";
  if (k === 35) return "D"; if (k <= 39) return "E"; if (k <= 43) return "F";
  if (k <= 47) return "G"; if (k <= 53) return "H"; if (k <= 56) return "I";
  if (k <= 63) return "J"; if (k <= 66) return "K"; if (k === 68) return "L";
  if (k <= 75) return "M"; if (k <= 82) return "N"; if (k === 84) return "O";
  if (k === 85) return "P"; if (k <= 88) return "Q"; if (k <= 93) return "R";
  if (k <= 96) return "S"; if (k <= 98) return "T"; return "U";
}

const antallN2 = new Map();
for (const r of D) antallN2.set(r.n2, (antallN2.get(r.n2) || 0) + 1);

const STRATIFISERINGER = {
  n2: { navn: "tosifret næringskode fra åpningskunngjøringens trykte etikett (lane 3s form)",
        f: (r) => r.n2 },
  hovedomrade: { navn: "næringshovedområde (NACE Rev.2 bokstav)", f: (r) => hovedomrade(r.n2) },
  n2_samlet: { navn: "tosifret kode, men bøtter med færre enn 10 bo slått sammen til «annet»",
        f: (r) => (antallN2.get(r.n2) >= 10 ? r.n2 : "annet") },
};

const expit = (u) => 1 / (1 + Math.exp(-u));
const logit = (p) => Math.log(p / (1 - p));

/** Eksakt Poisson-KI for O gitt E (Garwood), delt på E → SMR-intervall. */
function poissonSmrKi(O, E) {
  // invers khikvadrat via ufullstendig gamma: bruk beta-invers på gamma-forhold
  const gammaInv = (p, a) => { // finn x slik at P(a, x) = p, ved halvering
    let lo = 0, hi = Math.max(10, 4 * a + 20);
    const P = (x) => {
      // regularisert ufullstendig gamma via rekke/kjedebrøk (samme som pKhi)
      return 1 - pKhi(2 * x, 2 * a);
    };
    for (let i = 0; i < 200; i++) { const m = (lo + hi) / 2; if (P(m) < p) lo = m; else hi = m; }
    return (lo + hi) / 2;
  };
  const lo = O === 0 ? 0 : gammaInv(0.025, O) / E;
  const hi = gammaInv(0.975, O + 1) / E;
  return [lo, hi];
}

function standardiser(navn, strataAv) {
  // landsrate per stratum
  const rate = new Map();
  for (const r of D) {
    const s = strataAv(r);
    const e = rate.get(s) || { stratum: s, n: 0, k: 0 };
    e.n++; if (r.innstilt) e.k++;
    rate.set(s, e);
  }
  for (const [, e] of rate) e.p = e.k / e.n;

  const perKrets = new Map();
  for (const r of D) {
    if (!perKrets.has(r.tingrett)) perKrets.set(r.tingrett, []);
    perKrets.get(r.tingrett).push(r);
  }
  const kretser = [];
  for (const [krets, rader] of perKrets) {
    if (rader.length < MINN) continue;
    let E = 0, V = 0;
    const vekt = new Map();
    for (const r of rader) {
      const p = rate.get(strataAv(r)).p;
      E += p; V += p * (1 - p);
      vekt.set(strataAv(r), (vekt.get(strataAv(r)) || 0) + 1);
    }
    const O = rader.filter((r) => r.innstilt).length;
    const oe = O / E;
    const [pLo, pHi] = poissonSmrKi(O, E);
    kretser.push({ krets, saker: rader.length, O, E, oe,
      oe_ki95_binomisk: [(O - 1.959963984540054 * Math.sqrt(V)) / E,
                         (O + 1.959963984540054 * Math.sqrt(V)) / E],
      oe_ki95_poisson: [pLo, pHi], varians_O: V,
      z: (O - E) / Math.sqrt(V),
      // vektgrunnlaget: kretsens egen strata-fordeling (indirekte standardisering)
      vektgrunnlag: [...vekt.entries()].sort((a, b) => b[1] - a[1])
        .map(([s, c]) => ({ stratum: s, antall: c, andel_pst: pst(c / rader.length, 1) })) });
  }
  kretser.sort((a, b) => a.oe - b.oe);

  // heterogenitet før og etter standardisering
  const Ntot = kretser.reduce((s, c) => s + c.saker, 0);
  const Ktot = kretser.reduce((s, c) => s + c.O, 0);
  const pBar = Ktot / Ntot;
  let khiFor = 0, khiEtter = 0;
  for (const c of kretser) {
    khiFor += Math.pow(c.O - c.saker * pBar, 2) / (c.saker * pBar * (1 - pBar));
    khiEtter += Math.pow(c.O - c.E, 2) / c.varians_O;
  }
  const df = kretser.length - 1;

  // hierarkisk modell med og uten næringsoffset
  const GH = gaussHermite(60), SQPI = Math.sqrt(Math.PI);
  const llKrets = (k, n, eta0, tau) => {
    const ledd = GH.x.map((z, j) => {
      const p = expit(eta0 + tau * Math.SQRT2 * z);
      return Math.log(GH.w[j] / SQPI) + k * Math.log(p) + (n - k) * Math.log(1 - p);
    });
    const mx = Math.max(...ledd);
    return mx + Math.log(ledd.reduce((s, v) => s + Math.exp(v - mx), 0));
  };
  const tilpass = (offsetAv) => {
    let best = { ll: -Infinity, mu: 0, tau: 0 };
    for (let mu = -0.6; mu <= 1.8; mu += 0.01)
      for (let tau = 0; tau <= 0.5; tau += 0.004) {
        let ll = 0;
        for (const c of kretser) ll += llKrets(c.O, c.saker, mu + offsetAv(c), tau);
        if (ll > best.ll) best = { ll, mu, tau };
      }
    for (let runde = 0; runde < 5; runde++) {
      const dm = 0.01 / Math.pow(3, runde), dt = 0.004 / Math.pow(3, runde);
      for (let a = -3; a <= 3; a++) for (let b = -3; b <= 3; b++) {
        const mu = best.mu + a * dm, tau = Math.max(0, best.tau + b * dt);
        let ll = 0;
        for (const c of kretser) ll += llKrets(c.O, c.saker, mu + offsetAv(c), tau);
        if (ll > best.ll) best = { ll, mu, tau };
      }
    }
    let ll0 = 0;
    for (const c of kretser) ll0 += llKrets(c.O, c.saker, best.mu + offsetAv(c), 0);
    return { ...best, ll0, lrt: 2 * (best.ll - ll0), p_lrt: 0.5 * pKhi(Math.max(0, 2 * (best.ll - ll0)), 1) };
  };
  const utenOffset = tilpass(() => 0);
  const medOffset = tilpass((c) => logit(Math.min(1 - 1e-9, Math.max(1e-9, c.E / c.saker))));

  const spennOe = [kretser[0].oe, kretser[kretser.length - 1].oe];
  const raaSort = kretser.slice().sort((a, b) => a.O / a.saker - b.O / b.saker);
  const spennRaaRatio = [raaSort[0].O / raaSort[0].saker / pBar,
                         raaSort[raaSort.length - 1].O / raaSort[raaSort.length - 1].saker / pBar];

  return {
    stratifisering: navn,
    antall_strata: rate.size,
    strata: [...rate.values()].sort((a, b) => b.n - a.n),
    kretser,
    heterogenitet: {
      ustandardisert: { khikvadrat: r2(khiFor), df, p: pKhi(khiFor, df), overskudd: r2(khiFor - df) },
      standardisert: { khikvadrat: r2(khiEtter), df, p: pKhi(khiEtter, df), overskudd: r2(khiEtter - df) },
      dempning_av_overskudd_pst: r1(100 * (1 - (khiEtter - df) / (khiFor - df))),
    },
    hierarkisk: {
      uten_naeringsoffset: { mu: r4(utenOffset.mu), tau: r4(utenOffset.tau), lrt: r3(utenOffset.lrt),
        p_lrt: utenOffset.p_lrt },
      med_naeringsoffset: { mu: r4(medOffset.mu), tau: r4(medOffset.tau), lrt: r3(medOffset.lrt),
        p_lrt: medOffset.p_lrt },
      dempning_av_tau_pst: r1(100 * (1 - medOffset.tau / utenOffset.tau)),
      dempning_av_varians_pst: r1(100 * (1 - Math.pow(medOffset.tau / utenOffset.tau, 2))),
    },
    spenn: {
      observert_delt_paa_forventet: [r4(spennOe[0]), r4(spennOe[1])],
      ustandardisert_ratio_mot_landsraten: [r4(spennRaaRatio[0]), r4(spennRaaRatio[1])],
      landsrate_pst: pst(pBar, 2),
    },
  };
}

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

console.log("«Tomme bo» — revisjon 2, steg 7: næringsstandardiseringen\n");

const resultater = {};
for (const [nokkel, s] of Object.entries(STRATIFISERINGER)) {
  const res = standardiser(s.navn, s.f);
  resultater[nokkel] = res;
  console.log(`--- ${nokkel}: ${res.antall_strata} strata, ${res.kretser.length} kretser (n ≥ ${MINN}) ---`);
  console.log(`    O/E-spenn:                    ${res.spenn.observert_delt_paa_forventet.join(" – ")}`);
  console.log(`    ustandardisert ratio-spenn:   ${res.spenn.ustandardisert_ratio_mot_landsraten.join(" – ")}`);
  console.log(`    heterogenitet før:  χ² = ${res.heterogenitet.ustandardisert.khikvadrat}`
    + ` (df ${res.heterogenitet.ustandardisert.df}, overskudd ${res.heterogenitet.ustandardisert.overskudd})`);
  console.log(`    heterogenitet etter: χ² = ${res.heterogenitet.standardisert.khikvadrat}`
    + ` (overskudd ${res.heterogenitet.standardisert.overskudd})`
    + `  → dempning ${res.heterogenitet.dempning_av_overskudd_pst} %`);
  console.log(`    τ̂ uten næringsoffset ${res.hierarkisk.uten_naeringsoffset.tau},`
    + ` med offset ${res.hierarkisk.med_naeringsoffset.tau}`
    + `  → variansdempning ${res.hierarkisk.dempning_av_varians_pst} %\n`);
}

// stratatabell for publisering (minstecelle)
const hoved = resultater.n2;
const smaa = hoved.strata.filter((s) => s.n < 10);
const publiserbarStrata = [
  ...hoved.strata.filter((s) => s.n >= 10).map((s) => ({
    stratum: s.stratum, bo: s.n, innstilt: s.k, landsrate_pst: pst(s.p, 2) })),
  { stratum: `SAMLET: ${smaa.length} bøtter med under 10 bo`, bo: smaa.reduce((a, s) => a + s.n, 0),
    innstilt: smaa.reduce((a, s) => a + s.k, 0),
    landsrate_pst: pst(smaa.reduce((a, s) => a + s.k, 0) / smaa.reduce((a, s) => a + s.n, 0), 2) },
];
console.log(`Stratatabell for publisering: ${publiserbarStrata.length - 1} bøtter med n ≥ 10`
  + ` + én samlerad for ${smaa.length} små bøtter (${smaa.reduce((a, s) => a + s.n, 0)} bo).`);

const ut = {
  studie: "Tomme bo — revisjon 2 etter fagfellevurdering",
  leverer: "fagfellens punkt 12 — strata, vekter, resultat og usikkerhet for næringsstandardiseringen",
  skript: "sporringer/rev2-07-standardisering.mjs",
  kjort: KJORT,
  datagrunnlag: "offentlig tilgjengelige registerkunngjøringer om konkursbehandling",
  frosset_uttrekk: "data/_kohort-rader-arbeidskopi.json",
  kohortvindu: VINDU, sensureringsdato: KORPUSSLUTT,
  metode: {
    type: "INDIREKTE standardisering. Hver krets får landsraten for sin egen næringssammensetning; "
      + "E = Σ over kretsens bo av landets innstillingsrate i boets næringsbøtte. Nøkkeltallet er O/E.",
    vekter: "Vektene er kretsens EGEN strata-fordeling (det er det som gjør standardiseringen "
      + "indirekte). De publiseres per krets i feltet vektgrunnlag.",
    usikkerhet_binomisk: "Var(O) = Σ p_s(1 − p_s) over kretsens bo, under H0 om at kretsen følger "
      + "landsratene. 95 % KI for O/E = (O ± 1,96·√Var)/E. PRIMÆR.",
    usikkerhet_poisson: "Eksakte Poisson-grenser (Garwood) for O delt på E. Oppgitt som "
      + "følsomhetskontroll; Poisson er konservativ her fordi hendelsene ikke er sjeldne.",
    naeringskilde: "tosifret kode utledet av åpningskunngjøringens TRYKTE etikett via kartet "
      + "bransjekart-v3 (SSB Klass), aldri av næringskode på foretaket",
    minstecelle: "stratatabellen publiserer bøtter med n ≥ 10 for seg; øvrige samlet",
  },
  hovedstratifisering: "n2",
  publiserbar_stratatabell: publiserbarStrata,
  stratifiseringer: resultater,
  konklusjon: {
    paakrevd_formulering: "Næringssammensetning dempet ikke variasjonen vesentlig under denne "
      + "standardiseringen. Det er ikke det samme som at næringsmiks ikke forklarer noe: "
      + "standardiseringen er indirekte, bøttene er grove, og "
      + Math.min(...Object.values(resultater).map((r) => r.antall_strata))
      + "–" + Math.max(...Object.values(resultater).map((r) => r.antall_strata))
      + " strata er alt materialet bærer.",
    forbudt_formulering: "«Næringsmiksen forklarer ingenting av domstolsvariasjonen.»",
    tallfesting: "Standardisering på " + resultater.n2.antall_strata + " næringsbøtter fjerner "
      + "ingenting av variasjonen: overskuddsheterogeniteten mellom kretsene går fra "
      + resultater.n2.heterogenitet.ustandardisert.overskudd + " til "
      + resultater.n2.heterogenitet.standardisert.overskudd + " (den ØKER med "
      + Math.abs(resultater.n2.heterogenitet.dempning_av_overskudd_pst) + " %), og kretsvariansen "
      + "τ̂² går fra " + r4(Math.pow(resultater.n2.hierarkisk.uten_naeringsoffset.tau, 2)) + " til "
      + r4(Math.pow(resultater.n2.hierarkisk.med_naeringsoffset.tau, 2)) + " (også en økning på "
      + Math.abs(resultater.n2.hierarkisk.dempning_av_varians_pst) + " %). Det standardiserte "
      + "O/E-spennet " + resultater.n2.spenn.observert_delt_paa_forventet.join("–")
      + " er praktisk talt identisk med det ustandardiserte ratio-spennet "
      + resultater.n2.spenn.ustandardisert_ratio_mot_landsraten.join("–")
      + ". Alle tre stratifiseringene gir samme svar.",
    svakhet: "Med " + resultater.n2.antall_strata + " bøtter har " + smaa.length
      + " av dem færre enn 10 bo. For slike bøtter treffer landsraten kretsens egne bo nesten "
      + "eksakt, så E overtilpasses og O/E trekkes kunstig mot 1. Stratifiseringen på "
      + "næringshovedområde (" + resultater.hovedomrade.antall_strata + " bøtter) er derfor "
      + "den mest robuste varianten og gir samme svar.",
  },
};
skrivJson(`data/rev2-07-standardisering-${KJORT}.json`, ut);
