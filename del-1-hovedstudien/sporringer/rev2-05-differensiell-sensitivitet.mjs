// «Tomme bo» — REVISJON 2, steg 5: DIFFERENSIELL SENSITIVITET (fagfellens punkt 5).
//
// Manuskriptet håndterer i dag den høyere uavgjort-raten i bygg ved å tilordne
// SAMME eventuelle § 135-rate x til uavgjorte bo i begge grupper, og viser at
// ingen felles x i [0, 1] snur rekkefølgen (krysningspunkt x = 2,28). Algebraen
// er riktig, men like uavgjort-rater er en ANTAKELSE, ikke en verste-fall-analyse.
//
// Dette skriptet erstatter den med differensielle grenser:
//   (a) reproduserer den felles-x-algebraen og krysningspunktet;
//   (b) regner ut vippepunktkurven x_B*(x_O) — hvor høy den eventuelle raten må
//       være i bygg for hver antatt rate i øvrige for at rekkefølgen skal snu;
//   (c) finner den raten i øvrige der reversering blir matematisk umulig;
//   (d) regner det absolutte verste tilfellet (alle uavgjorte byggbo blir § 135,
//       ingen av de øvrige);
//   (e) finner hvor mange av de 111 uavgjorte byggboene som må bli § 135 før
//       forskjellen slutter å være statistisk skillbar (Fishers eksakte test);
//   (f) EMPIRISK ANKER: et landemerke-estimat av hva x faktisk er i hver gruppe,
//       målt på de boene som var uavgjorte ved dag 365 og har full oppfølging til
//       dag 730 — altså om antakelsen x_B = x_O i det hele tatt er holdbar.
//
// READ-ONLY. Ingen databasetilgang. Kjøres:
//   node sporringer/rev2-05-differensiell-sensitivitet.mjs

import { lesKohort, clopperPearson, newcombe, fisherEksakt, aalenJohansen, ajF,
         skrivJson, pst, r1, r2, r3, r4, KJORT, KORPUSSLUTT, VINDU, H12, H24 } from "./rev2-00-lib.mjs";

// Talljournalens tre-tilstandsfordeling (randregel «tidligst» = kanonisk telling).
const D = lesKohort("tidligst");
const BY = D.filter((r) => r.bygg), OV = D.filter((r) => !r.bygg);

const eB = BY.filter((r) => r.innstilt).length;              // 911
const nB = BY.length;                                        // 1280
const uB = BY.filter((r) => r.utfall === "fortsatt_apen").length; // 111
const eO = OV.filter((r) => r.innstilt).length;              // 2986
const nO = OV.length;                                        // 3885
const uO = OV.filter((r) => r.utfall === "fortsatt_apen").length; // 240

const pB = eB / nB, pO = eO / nO;

console.log("«Tomme bo» — revisjon 2, steg 5: differensiell sensitivitet for de uavgjorte boene\n");
console.log(`  bygg   : ${eB} innstilt av ${nB} = ${pst(pB, 2)} %, ${uB} uavgjorte (${pst(uB / nB, 2)} %)`);
console.log(`  øvrige : ${eO} innstilt av ${nO} = ${pst(pO, 2)} %, ${uO} uavgjorte (${pst(uO / nO, 2)} %)`);
console.log(`  differanse i dag: ${pst(pB - pO, 2)} pp\n`);

// ---------------------------------------------------------------------------
// (a) felles x — manuskriptets nåværende sensitivitet
// ---------------------------------------------------------------------------
// (eB + x·uB)/nB = (eO + x·uO)/nO  ⇔  x·(uB/nB − uO/nO) = eO/nO − eB/nB
const felles_x = (eO / nO - eB / nB) / (uB / nB - uO / nO);
console.log("(a) FELLES x (manuskriptets nåværende form)");
console.log(`    krysningspunkt x = ${r4(felles_x)}  →  ${felles_x > 1 ? "utenfor [0, 1]: ingen felles rate kan snu rekkefølgen"
  : "INNENFOR [0, 1]"}`);
console.log(`    ved x = 1 (alle uavgjorte blir § 135 i begge grupper):`
  + ` bygg ${pst((eB + uB) / nB, 2)} % mot øvrige ${pst((eO + uO) / nO, 2)} %\n`);

// ---------------------------------------------------------------------------
// (b) vippepunktkurven x_B*(x_O)
// ---------------------------------------------------------------------------
// Reversering ⇔ (eB + x_B·uB)/nB > (eO + x_O·uO)/nO
//            ⇔ x_B > [ nB·(eO + x_O·uO)/nO − eB ] / uB
const xBkrav = (xO) => (nB * (eO + xO * uO) / nO - eB) / uB;
const rutenett = [];
for (let i = 0; i <= 20; i++) {
  const xO = i / 20;
  const krav = xBkrav(xO);
  rutenett.push({
    antatt_rate_ovrige_pst: pst(xO, 1),
    kreves_rate_bygg_for_reversering_pst: krav > 1 ? null : pst(krav, 1),
    kreves_antall_av_111: krav > 1 ? null : Math.ceil(krav * uB),
    mulig: krav <= 1,
    andel_bygg_ved_kravet_pst: krav > 1 ? null : pst((eB + krav * uB) / nB, 2),
    andel_ovrige_pst: pst((eO + xO * uO) / nO, 2),
  });
}
console.log("(b) VIPPEPUNKTKURVE — hvor høy eventuell § 135-rate kreves i bygg for at rekkefølgen skal snu?");
console.log("    antatt rate  |  kreves i bygg  |  som antall av de 111  |  gir andeler");
for (const r of rutenett.filter((_, i) => i % 2 === 0))
  console.log(`    ${String(r.antatt_rate_ovrige_pst).padStart(8)} %  |`
    + `${r.mulig ? String(r.kreves_rate_bygg_for_reversering_pst).padStart(13) + " %" : "        UMULIG "}  |`
    + `${r.mulig ? String(r.kreves_antall_av_111).padStart(19) : "                  –"}     |`
    + `${r.mulig ? ` ${r.andel_bygg_ved_kravet_pst} % mot ${r.andel_ovrige_pst} %` : "  –"}`);

// ---------------------------------------------------------------------------
// (c) hvor reversering blir umulig
// ---------------------------------------------------------------------------
// x_B = 1 gir maksimal byggandel (eB + uB)/nB. Reversering umulig når
// (eO + x_O·uO)/nO ≥ (eB + uB)/nB  ⇔  x_O ≥ [ nO·(eB + uB)/nB − eO ] / uO
const xOgrense = (nO * (eB + uB) / nB - eO) / uO;
console.log(`\n(c) Reversering er MATEMATISK UMULIG når den eventuelle raten blant øvriges uavgjorte`);
console.log(`    bo overstiger ${pst(xOgrense, 1)} % (= ${Math.ceil(xOgrense * uO)} av ${uO} bo).`);

// ---------------------------------------------------------------------------
// (d) det absolutte verste tilfellet
// ---------------------------------------------------------------------------
const verste = { bygg: (eB + uB) / nB, ovrige: eO / nO };
const [vlo, vhi] = newcombe(eB + uB, nB, eO, nO);
console.log(`\n(d) VERSTE TILFELLE (alle ${uB} uavgjorte byggbo blir § 135, ingen av de ${uO} øvrige):`);
console.log(`    ${eB + uB}/${nB} = ${pst(verste.bygg, 2)} % mot ${eO}/${nO} = ${pst(verste.ovrige, 2)} %`
  + `  → +${pst(verste.bygg - verste.ovrige, 2)} pp, Newcombe-KI [${pst(vlo, 2)}, ${pst(vhi, 2)}] pp`);
console.log(`    Rekkefølgen SNUR i dette scenariet. Det er derfor formuleringen må være`);
console.log(`    «ingen FELLES eventuell rate kan snu rekkefølgen», ikke «reversering er umulig».`);

// ---------------------------------------------------------------------------
// (e) når slutter forskjellen å være statistisk skillbar?
// ---------------------------------------------------------------------------
const signifikansgrense = [];
let forstIkkeSig = null, forstSnudd = null;
for (let k = 0; k <= uB; k++) {
  const a = eB + k, b = nB - a, c = eO, d = nO - eO;
  const p = fisherEksakt(a, b, c, d);
  if (forstIkkeSig === null && p > 0.05) forstIkkeSig = { k, p, andel_bygg_pst: pst(a / nB, 2) };
  if (forstSnudd === null && a / nB > eO / nO) forstSnudd = { k, p, andel_bygg_pst: pst(a / nB, 2) };
  if (k % 10 === 0 || k === uB)
    signifikansgrense.push({ antall_av_111: k, andel_bygg_pst: pst(a / nB, 2),
      differanse_pp: pst(a / nB - eO / nO, 2), fisher_p: p < 1e-4 ? p.toExponential(2) : r4(p) });
}
console.log(`\n(e) STATISTISK SKILLBARHET (x_O = 0; Fishers eksakte tosidige test)`);
console.log(`    forskjellen slutter å være signifikant på 5 %-nivå når ${forstIkkeSig.k} av de ${uB}`
  + ` uavgjorte byggboene blir § 135 (bygg ${forstIkkeSig.andel_bygg_pst} %, p = ${r4(forstIkkeSig.p)})`);
console.log(`    rekkefølgen snur ved ${forstSnudd.k} av ${uB} (bygg ${forstSnudd.andel_bygg_pst} %`
  + ` mot øvrige ${pst(pO, 2)} %)`);

// ---------------------------------------------------------------------------
// (f) EMPIRISK ANKER — er antakelsen x_B = x_O holdbar?
// ---------------------------------------------------------------------------
/**
 * Landemerke-estimat. Blant bo som fortsatt var uavgjorte ved dag L og som har
 * minst L + Δ dagers oppfølging: hvor stor andel fikk § 135 innen dag L + Δ?
 * Ingen sensurering innenfor vinduet, så andelen er en ren binomisk andel.
 */
function landemerke(gruppe, L, delta) {
  const d = gruppe.filter((r) => r.oppfolging >= L + delta && r.t > L);
  const k = d.filter((r) => r.arsak === 1 && r.t <= L + delta).length;
  const a = d.filter((r) => r.arsak === 2 && r.t <= L + delta).length;
  const [lo, hi] = clopperPearson(k, d.length);
  return { landemerke_dag: L, vindu_dager: delta, n_uavgjorte_ved_L: d.length,
    fikk_135: k, fikk_ordinaer_avslutning: a, fortsatt_uavgjort_ved_slutt: d.length - k - a,
    andel_135_pst: pst(k / d.length, 2), clopper_pearson95_pst: [pst(lo, 2), pst(hi, 2)] };
}
const ankere = [];
for (const [L, dlt] of [[365, 365], [548, 182], [365, 236]]) {
  const lb = landemerke(BY, L, dlt), lo2 = landemerke(OV, L, dlt);
  const [dlo, dhi] = newcombe(lb.fikk_135, lb.n_uavgjorte_ved_L, lo2.fikk_135, lo2.n_uavgjorte_ved_L);
  ankere.push({ bygg: lb, ovrige: lo2, differanse_pp: pst(lb.fikk_135 / lb.n_uavgjorte_ved_L
    - lo2.fikk_135 / lo2.n_uavgjorte_ved_L, 2), newcombe95_pp: [pst(dlo, 2), pst(dhi, 2)],
    fisher_p: fisherEksakt(lb.fikk_135, lb.n_uavgjorte_ved_L - lb.fikk_135,
      lo2.fikk_135, lo2.n_uavgjorte_ved_L - lo2.fikk_135) });
}
console.log("\n(f) EMPIRISK ANKER — hva er x faktisk? (landemerke: bo uavgjorte ved dag L, fulgt Δ dager til)");
for (const a of ankere)
  console.log(`    L = ${a.bygg.landemerke_dag}, Δ = ${a.bygg.vindu_dager}:`
    + ` bygg ${a.bygg.fikk_135}/${a.bygg.n_uavgjorte_ved_L} = ${a.bygg.andel_135_pst} %`
    + ` [${a.bygg.clopper_pearson95_pst.join("–")}]  mot`
    + ` øvrige ${a.ovrige.fikk_135}/${a.ovrige.n_uavgjorte_ved_L} = ${a.ovrige.andel_135_pst} %`
    + ` [${a.ovrige.clopper_pearson95_pst.join("–")}]`
    + `  differanse ${a.differanse_pp} pp [${a.newcombe95_pp.join(", ")}], Fisher p = ${r3(a.fisher_p)}`);

const ut = {
  studie: "Tomme bo — revisjon 2 etter fagfellevurdering",
  leverer: "fagfellens punkt 5 — differensielle sensitivitetsgrenser for de uavgjorte boene",
  skript: "sporringer/rev2-05-differensiell-sensitivitet.mjs",
  kjort: KJORT,
  datagrunnlag: "offentlig tilgjengelige registerkunngjøringer om konkursbehandling",
  frosset_uttrekk: "data/_kohort-rader-arbeidskopi.json",
  kohortvindu: VINDU,
  sensureringsdato: KORPUSSLUTT,
  grunntall: { bygg: { innstilt: eB, n: nB, uavgjorte: uB, andel_pst: pst(pB, 2) },
    ovrige: { innstilt: eO, n: nO, uavgjorte: uO, andel_pst: pst(pO, 2) },
    differanse_pp: pst(pB - pO, 2) },

  a_felles_x: {
    formel: "(eB + x·uB)/nB = (eO + x·uO)/nO",
    krysningspunkt_x: r4(felles_x),
    tolkning: "Krysningspunktet ligger utenfor [0, 1]. Ingen FELLES eventuell § 135-rate anvendt på "
      + "uavgjorte bo i begge grupper kan snu rekkefølgen. Dette er en betinget, ikke en "
      + "verste-fall-analyse, og skal aldri formuleres som at reversering er umulig.",
    ved_x_1: { bygg_pst: pst((eB + uB) / nB, 2), ovrige_pst: pst((eO + uO) / nO, 2) },
  },

  b_vippepunktkurve: {
    formel: "x_B*(x_O) = [ nB·(eO + x_O·uO)/nO − eB ] / uB — reversering krever x_B > x_B*",
    ankerpunkter: {
      ved_0_pst_i_ovrige: { kreves_i_bygg_pst: pst(xBkrav(0), 1), som_antall_av_111: Math.ceil(xBkrav(0) * uB) },
      ved_25_pst_i_ovrige: { kreves_i_bygg_pst: pst(xBkrav(0.25), 1), som_antall_av_111: Math.ceil(xBkrav(0.25) * uB) },
      ved_50_pst_i_ovrige: { kreves_i_bygg_pst: xBkrav(0.5) > 1 ? null : pst(xBkrav(0.5), 1),
        mulig: xBkrav(0.5) <= 1 },
    },
    rutenett_20_punkter: rutenett,
  },

  c_umulighetsgrense: {
    formel: "x_O ≥ [ nO·(eB + uB)/nB − eO ] / uO",
    grense_pst: pst(xOgrense, 2),
    som_antall_av_240: Math.ceil(xOgrense * uO),
    tolkning: "Blir mer enn " + pst(xOgrense, 1) + " % av øvriges uavgjorte bo innstilt, kan bygg ikke "
      + "passere øvrige uansett hva som skjer med byggs egne uavgjorte bo.",
  },

  d_verste_tilfelle: {
    scenario: "alle " + uB + " uavgjorte byggbo blir § 135; ingen av de " + uO + " øvrige gjør det",
    bygg: [eB + uB, nB, pst(verste.bygg, 2)], ovrige: [eO, nO, pst(verste.ovrige, 2)],
    differanse_pp: pst(verste.bygg - verste.ovrige, 2),
    newcombe95_pp: [pst(vlo, 2), pst(vhi, 2)],
    rekkefolgen_snur: verste.bygg > verste.ovrige,
    paakrevd_formulering: "Rekkefølgen kan ikke snus under noen FELLES eventuell § 135-rate anvendt på "
      + "uavgjorte bo i begge grupper. Den kan snus under tilstrekkelig ulike rater: i det ytterste "
      + "tilfellet, der alle uavgjorte byggbo blir innstilt og ingen av de øvrige gjør det, blir "
      + "byggandelen " + pst(verste.bygg, 1) + " % mot " + pst(verste.ovrige, 1) + " %.",
  },

  e_statistisk_skillbarhet: {
    forutsetning: "x_O = 0 (ingen av øvriges uavgjorte bo blir § 135) — det mest byggfiendtlige scenariet",
    test: "Fishers eksakte tosidige test",
    ikke_lenger_signifikant_ved: forstIkkeSig,
    rekkefolgen_snur_ved: forstSnudd,
    tabell: signifikansgrense,
  },

  f_empirisk_anker: {
    sporsmal: "Er antakelsen x_bygg = x_øvrige i det hele tatt holdbar?",
    metode: "Landemerke-analyse. Blant bo som fortsatt var uavgjorte ved dag L OG har minst "
      + "L + Δ dagers oppfølging, andelen som fikk § 135-kunngjøring innen dag L + Δ. "
      + "Ingen sensurering innenfor vinduet, så andelen er en ren binomisk andel.",
    landemerker: ankere,
    tolkning: "Ratene ligger nær hverandre og intervallene overlapper i alle tre vinduene. "
      + "Det gir empirisk støtte til at x_bygg og x_øvrige er av samme størrelsesorden, men det "
      + "ERSTATTER ikke den differensielle grensen — det gjør den bare mindre bekymringsfull.",
  },

  hovedbudskap: "Den differensielle grensen er den ærlige sensitiviteten. Den forsvinner likevel i "
    + "praksis når gruppene sammenliknes ved en FAST HORISONT med kumulativ insidens "
    + "(rev2-02/rev2-03): der finnes ingen uavgjorte bo å tilordne en rate til, fordi hvert bo "
    + "bidrar med den tiden det faktisk er observert. 24-måneders risikodifferanse er "
    + "−5,70 pp [−8,56, −2,83], praktisk talt identisk med as-of-differansen −5,69 pp.",
};
skrivJson(`data/rev2-05-differensiell-sensitivitet-${KJORT}.json`, ut);
