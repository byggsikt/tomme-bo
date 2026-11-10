// «Tomme bo» — REVISJON 2, steg 1: VALIDERING av revisjonsbiblioteket.
//
// Ingen nye tall publiseres før biblioteket reproduserer talljournalens låste
// verdier fra det frosne kohortuttrekket. Feiler en assertsjon, stopper skriptet.
// READ-ONLY, ingen databasetilgang.
//
// Kjøres: node sporringer/rev2-01-validering.mjs

import { lesKohort, aalenJohansen, ajF, ajKvantil, kmAlle, risikotabell,
         skrivJson, pst, r1, KJORT, KORPUSSLUTT } from "./rev2-00-lib.mjs";

const feil = [];
const sjekk = (navn, faktisk, forventet, tol = 0) => {
  const ok = tol === 0 ? faktisk === forventet : Math.abs(faktisk - forventet) <= tol;
  console.log(`  ${ok ? "OK  " : "FEIL"}  ${navn}: ${faktisk} (forventet ${forventet}${tol ? " ±" + tol : ""})`);
  if (!ok) feil.push({ navn, faktisk, forventet, tol });
  return ok;
};

const D = lesKohort("sensurert");
const B = D.filter((r) => r.bygg), O = D.filter((r) => !r.bygg);

console.log("A — kohort og hovedutfall (talljournal A1–A4, B1–B3, B6)");
sjekk("A1 kohort", D.length, 5165);
sjekk("A2 innstilt", D.filter((r) => r.innstilt).length, 3897);
sjekk("A2 andel %", +pst(D.filter((r) => r.innstilt).length / D.length), 75.5);
sjekk("A3 kun avsluttet", D.filter((r) => r.utfall === "avsluttet").length, 917);
sjekk("A4 fortsatt åpne", D.filter((r) => r.utfall === "fortsatt_apen").length, 351);
sjekk("A5 begge", D.filter((r) => r.utfall === "begge").length, 6);
sjekk("A6 min oppfølging", Math.min(...D.map((r) => r.oppfolging)), 601);
sjekk("A6 maks oppfølging", Math.max(...D.map((r) => r.oppfolging)), 1088);
sjekk("B1 bygg utførende", B.length, 1280);
sjekk("B2 bygg innstilt", B.filter((r) => r.innstilt).length, 911);
sjekk("B3 bygg avsluttet", B.filter((r) => r.utfall === "avsluttet").length, 258);
sjekk("B3 bygg åpne", B.filter((r) => r.utfall === "fortsatt_apen").length, 111);
sjekk("B4 område F", D.filter((r) => r.byggF).length, 1411);
sjekk("B6 øvrige", O.length, 3885);
sjekk("B6 øvrige innstilt", O.filter((r) => r.innstilt).length, 2986);
sjekk("E1 rettskretser", new Set(D.map((r) => r.tingrett)).size, 23);

console.log("\nD — varighet (talljournal D1–D4). Randregel 'sensurert' = kontroll-01s form,");
console.log("    som ga 178,5 / 144 og 267 / 205 / 57,1 / 65,2.");
const kv = (a, p) => { const s = a.slice().sort((x, y) => x - y); const i = (s.length - 1) * p, lo = Math.floor(i), hi = Math.ceil(i); return lo === hi ? s[lo] : s[lo] + (s[hi] - s[lo]) * (i - lo); };
const dB = B.filter((r) => r.arsak === 1).map((r) => r.t);
const dO = O.filter((r) => r.arsak === 1).map((r) => r.t);
sjekk("D1 rå median bygg (kontroll-01-form)", kv(dB, 0.5), 178.5);
sjekk("D1 rå median øvrige (kontroll-01-form)", kv(dO, 0.5), 144);
sjekk("D1 kvartiler bygg", `${kv(dB, 0.25)}/${kv(dB, 0.75)}`, "101/312");
sjekk("D1 rå median alle", kv(D.filter((r) => r.arsak === 1).map((r) => r.t), 0.5), 152);

const ajB = aalenJohansen(B), ajO = aalenJohansen(O);
sjekk("D3 CIF-median bygg", ajKvantil(ajB, 0.5), 267);
sjekk("D3 CIF-median øvrige", ajKvantil(ajO, 0.5), 205);
sjekk("D3 CIF 60 % bygg", ajKvantil(ajB, 0.6), 389);
sjekk("D3 CIF 60 % øvrige", ajKvantil(ajO, 0.6), 292);
sjekk("D4 CIF ved 365 d, bygg %", +pst(ajF(ajB, 365)), 57.1, 0.05);
sjekk("D4 CIF ved 365 d, øvrige %", +pst(ajF(ajO, 365)), 65.2, 0.05);

// Kaplan–Meier-median (D2) — merk: KM behandler ordinær avslutning som
// sensurering og OVERVURDERER innstillingsandelen; tas kun med som reproduksjon.
function kmMedian(data) {
  const rt = risikotabell(data);
  let S = 1;
  for (const r of rt) { if (r.d1 > 0) { S *= 1 - r.d1 / r.n; if (S <= 0.5) return r.t; } }
  return null;
}
sjekk("D2 KM-median bygg", kmMedian(B), 257);
sjekk("D2 KM-median øvrige", kmMedian(O), 203);

console.log("\nRandtilfellene (3 av 5 165): grensene av de to randreglene");
const D2 = lesKohort("tidligst");
const B2 = D2.filter((r) => r.bygg), O2 = D2.filter((r) => !r.bygg);
const ajB2 = aalenJohansen(B2), ajO2 = aalenJohansen(O2);
console.log(`  randtilfeller: ${D.filter((r) => r.randtilfelle).length} (bygg ${B.filter((r) => r.randtilfelle).length}, øvrige ${O.filter((r) => r.randtilfelle).length})`);
console.log(`  CIF(730) bygg   : ${pst(ajF(ajB, 730), 2)} % (sensurert) .. ${pst(ajF(ajB2, 730), 2)} % (tidligst)`);
console.log(`  CIF(730) øvrige : ${pst(ajF(ajO, 730), 2)} % (sensurert) .. ${pst(ajF(ajO2, 730), 2)} % (tidligst)`);
console.log(`  CIF-median bygg : ${ajKvantil(ajB, 0.5)} .. ${ajKvantil(ajB2, 0.5)} dager`);
console.log(`  CIF-median øvr. : ${ajKvantil(ajO, 0.5)} .. ${ajKvantil(ajO2, 0.5)} dager`);

const ut = {
  studie: "Tomme bo — revisjon 2 etter fagfellevurdering",
  skript: "sporringer/rev2-01-validering.mjs",
  kjort: KJORT,
  datagrunnlag: "offentlig tilgjengelige registerkunngjøringer om konkursbehandling",
  frosset_uttrekk: "data/_kohort-rader-arbeidskopi.json",
  sensureringsdato: KORPUSSLUTT,
  antall_sjekker: 26,
  feilende: feil.length,
  feil,
  randtilfeller: {
    antall: D.filter((r) => r.randtilfelle).length,
    bygg: B.filter((r) => r.randtilfelle).length,
    ovrige: O.filter((r) => r.randtilfelle).length,
    forklaring: "Tre foretak bærer en eldre innstilling FØR åpningen (utgått tidligere konkursløp). "
      + "Talljournalen teller dem som innstilt; det frosne uttrekket bærer ikke datoen for innstillingen "
      + "etter åpningen. Primæranalysen sensurerer dem ved korpusslutt (NEDRE grense for insidensen); "
      + "grenseanalysen setter hendelsen til dag 1 (ØVRE grense).",
    cif730_bygg_grenser_pst: [pst(ajF(ajB, 730), 2), pst(ajF(ajB2, 730), 2)],
    cif730_ovrige_grenser_pst: [pst(ajF(ajO, 730), 2), pst(ajF(ajO2, 730), 2)],
    cifmedian_bygg_grenser: [ajKvantil(ajB, 0.5), ajKvantil(ajB2, 0.5)],
    cifmedian_ovrige_grenser: [ajKvantil(ajO, 0.5), ajKvantil(ajO2, 0.5)],
  },
};
skrivJson(`data/rev2-01-validering-${KJORT}.json`, ut);

if (feil.length) { console.error(`\nSTOPP: ${feil.length} assertsjon(er) feilet.`); process.exit(1); }
console.log("\nAlle assertsjoner passerte — biblioteket reproduserer talljournalen.");
