// «Tomme bo» — REVISJON 2, steg 2: FASTHORISONT-ESTIMATET (fagfellens punkt 4).
//
// Fagfellen: 75,5 % er en observert as-of-andel, ikke en fasthorisont-
// sannsynlighet. Kohortens oppfølging spenner 601–1 088 dager, så hvert bo har
// hatt ulik mulighet til å oppleve utfallet. Det formelt korrekte primærestimatet
// er 24-måneders kumulativ insidens for § 135-innstilling, estimert med
// Aalen–Johansen med ordinær avslutning som konkurrerende hendelse.
//
// Dette skriptet leverer 12-, 18- og 24-måneders kumulativ insidens for
//   (a) hele kohorten, (b) utførende bygg og anlegg, (c) øvrige næringer,
// med 95 % KI (log(−log)-transformert), risikomengder, den konkurrerende
// hendelsens insidens og den fortsatt-uavgjorte andelen — slik at de tre
// summerer til 1 på hver horisont.
//
// READ-ONLY. Ingen databasetilgang. Kjøres:
//   node sporringer/rev2-02-kumulativ-insidens.mjs

import { lesKohort, aalenJohansen, ajF, ajKI, ajVar, risikoVed, kmAlle,
         clopperPearson, skrivJson, pst, r1, r3,
         KJORT, KORPUSSLUTT, VINDU, H12, H18, H24 } from "./rev2-00-lib.mjs";

const HORISONTER = [
  { navn: "12 mnd", dager: H12 },
  { navn: "18 mnd", dager: H18 },
  { navn: "24 mnd", dager: H24 },
];

/**
 * Kaplan–Meier for ALLE årsaker (§ 135 ELLER ordinær avslutning), evaluert i t.
 * S(t) = andelen bo som verken er innstilt eller avsluttet innen dag t.
 * Kontrollidentiteten CIF1(t) + CIF2(t) + S(t) = 1 skal holde eksakt.
 */
function sAlle(data, t) {
  const m = new Map();
  for (const r of data) {
    const e = m.get(r.t) || { t: r.t, d: 0, tot: 0 };
    if (r.arsak !== 0) e.d++;
    e.tot++;
    m.set(r.t, e);
  }
  const rader = [...m.values()].sort((a, b) => a.t - b.t);
  let n = data.length, S = 1;
  for (const r of rader) {
    if (r.t > t) break;
    if (r.d > 0) S *= 1 - r.d / n;
    n -= r.tot;
  }
  return S;
}

/** Aalen–Johansen for den KONKURRERENDE hendelsen (årsak 2). */
function ajKonkurrent(data) {
  return aalenJohansen(data.map((r) => ({ ...r, arsak: r.arsak === 1 ? 2 : r.arsak === 2 ? 1 : 0 })));
}

function analyser(navn, data) {
  const aj = aalenJohansen(data);
  const ajK = ajKonkurrent(data);
  const innstilt = data.filter((r) => r.arsak === 1).length;
  const rader = HORISONTER.map((h) => {
    const [lav, hoy, se] = ajKI(aj, h.dager, "loglog");
    const [wlav, whoy] = ajKI(aj, h.dager, "wald");
    const F = ajF(aj, h.dager);
    const Fk = ajF(ajK, h.dager);
    const S = sAlle(data, h.dager);
    return {
      horisont: h.navn,
      dager: h.dager,
      cif_innstilling_pst: pst(F, 2),
      ki95_lav_pst: pst(lav, 2),
      ki95_hoy_pst: pst(hoy, 2),
      se_pst: pst(se, 3),
      ki95_wald_pst: [pst(wlav, 2), pst(whoy, 2)],
      cif_ordinaer_avslutning_pst: pst(Fk, 2),
      fortsatt_uavgjort_pst: pst(S, 2),
      sum_kontroll_pst: pst(F + Fk + S, 3),
      risikomengde: risikoVed(data, h.dager),
      hendelser_innen_horisont: data.filter((r) => r.arsak === 1 && r.t <= h.dager).length,
      konkurrenthendelser_innen_horisont: data.filter((r) => r.arsak === 2 && r.t <= h.dager).length,
    };
  });
  const [cpLav, cpHoy] = clopperPearson(innstilt, data.length);

  // Antakelsesfri kontroll: delkohorten med FULL oppfølging til hver horisont.
  // Her finnes ingen sensurering innenfor horisonten, så andelen er en ren
  // binomisk andel og krever ingen konkurrerende-risiko-estimator i det hele tatt.
  const komplett = HORISONTER.map((h) => {
    const d = data.filter((r) => r.oppfolging >= h.dager);
    const k = d.filter((r) => r.arsak === 1 && r.t <= h.dager).length;
    const [lo, hi] = clopperPearson(k, d.length);
    return { horisont: h.navn, dager: h.dager, n_full_oppfolging: d.length,
      innstilt_innen: k, andel_pst: pst(k / d.length, 2),
      clopper_pearson95_pst: [pst(lo, 2), pst(hi, 2)] };
  });

  return {
    gruppe: navn,
    n: data.length,
    komplett_oppfolging_delkohort: komplett,
    observert_asof: {
      innstilt: innstilt,
      andel_pst: pst(innstilt / data.length, 2),
      clopper_pearson95_pst: [pst(cpLav, 1), pst(cpHoy, 1)],
      merknad: "Observert kumulativ andel per " + KORPUSSLUTT
        + " — ikke en fasthorisont-sannsynlighet. Oppfølgingstiden varierer mellom boene.",
    },
    horisonter: rader,
  };
}

console.log("«Tomme bo» — revisjon 2, steg 2: fasthorisont kumulativ insidens\n");

const resultat = {};
for (const randregel of ["sensurert", "tidligst"]) {
  const D = lesKohort(randregel);
  const B = D.filter((r) => r.bygg);
  const O = D.filter((r) => !r.bygg);
  resultat[randregel] = {
    alle: analyser("hele kohorten", D),
    bygg: analyser("utførende bygg og anlegg", B),
    ovrige: analyser("øvrige næringer", O),
  };
  if (randregel === "sensurert") {
    for (const g of ["alle", "bygg", "ovrige"]) {
      const r = resultat[randregel][g];
      console.log(`${r.gruppe} (n = ${r.n})`);
      console.log(`  observert as-of ${KORPUSSLUTT}: ${r.observert_asof.andel_pst} %`
        + ` [${r.observert_asof.clopper_pearson95_pst.join("–")}]`);
      for (const h of r.horisonter) {
        console.log(`  CIF ${h.horisont} (${h.dager} d): ${h.cif_innstilling_pst} %`
          + ` [${h.ki95_lav_pst}–${h.ki95_hoy_pst}]   risikomengde ${h.risikomengde}`
          + `   (avslutning ${h.cif_ordinaer_avslutning_pst} %, uavgjort ${h.fortsatt_uavgjort_pst} %,`
          + ` sum ${h.sum_kontroll_pst})`);
      }
      for (const k of r.komplett_oppfolging_delkohort)
        console.log(`  antakelsesfri kontroll ${k.horisont}: ${k.innstilt_innen}/${k.n_full_oppfolging}`
          + ` = ${k.andel_pst} % [${k.clopper_pearson95_pst.join("–")}]  (kun bo med full oppfølging)`);
      console.log("");
    }
  }
}

// Randtilfellenes bidrag på primærhorisonten
const grense = {};
for (const g of ["alle", "bygg", "ovrige"]) {
  const a = resultat.sensurert[g].horisonter.find((h) => h.dager === H24);
  const b = resultat.tidligst[g].horisonter.find((h) => h.dager === H24);
  grense[g] = { sensurert_pst: a.cif_innstilling_pst, tidligst_pst: b.cif_innstilling_pst,
    spenn_pp: r3(b.cif_innstilling_pst - a.cif_innstilling_pst) };
}
console.log("Randtilfellenes (3 av 5 165) effekt på 24-måneders CIF:");
for (const [g, v] of Object.entries(grense))
  console.log(`  ${g}: ${v.sensurert_pst} % .. ${v.tidligst_pst} % (spenn ${v.spenn_pp} pp)`);

const ut = {
  studie: "Tomme bo — revisjon 2 etter fagfellevurdering",
  leverer: "fagfellens punkt 4 — fasthorisont Aalen–Johansen som primærestimat",
  skript: "sporringer/rev2-02-kumulativ-insidens.mjs",
  kjort: KJORT,
  datagrunnlag: "offentlig tilgjengelige registerkunngjøringer om konkursbehandling",
  frosset_uttrekk: "data/_kohort-rader-arbeidskopi.json",
  kohortvindu: VINDU,
  sensureringsdato: KORPUSSLUTT,
  metode: {
    estimator: "Aalen–Johansen, kumulativ insidensfunksjon for årsak 1 (§ 135-innstilling)",
    konkurrerende_hendelse: "ordinær avslutning av bobehandlingen",
    varians: "deltametoden (Marubini & Valsecchi 1995; Klein & Moeschberger kap. 4)",
    konfidensintervall: "95 %, log(−log)-transformert (holder seg i (0,1)); Wald-varianten oppgitt ved siden av",
    horisonter: "12 mnd = 365 dager, 18 mnd = 548 dager, 24 mnd = 730 dager (hele dager fra åpningsdato)",
    risikomengde: "ordinær risikomengde Y(t) = antall bo med observert tid ≥ t",
    randregel_primaer: "sensurert (3 randtilfeller sensureres ved korpusslutt — gir NEDRE grense)",
    randregel_grense: "tidligst (samme 3 gis hendelse på dag 1 — gir ØVRE grense)",
    inferensmaal: "Kohortandelen er eksakt for denne observerte endelige kohorten. Konfidensintervallene "
      + "er modellbaserte inferenssammendrag for en videre prosess av sammenliknbare norske "
      + "AS/ASA-forankrede konkursbo, under antatt uavhengighet mellom bo.",
  },
  primaer_randregel_sensurert: resultat.sensurert,
  grense_randregel_tidligst: resultat.tidligst,
  randtilfellenes_effekt_24mnd: grense,
};
skrivJson(`data/rev2-02-kumulativ-insidens-${KJORT}.json`, ut);
