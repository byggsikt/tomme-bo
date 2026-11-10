// «Tomme bo» — REVISJON 2, steg 3: GRAYS TEST og RISIKODIFFERANSEN (fagfellens punkt 6).
//
// Fagfellen: den primære gruppesammenlikningen bør være en direkte
// kumulativ-insidens-kontrast — Grays test for likhet mellom
// kumulativ-insidens-kurvene, og risikodifferansen ved en fast horisont med KI —
// framfor en khikvadrattest på den observerte as-of-andelen.
//
// Leverer:
//   (a) Grays test (Gray 1988, ρ = 0) for bygg mot øvrige;
//   (b) risikodifferansen CIF_bygg(t) − CIF_øvrige(t) ved 12/18/24 måneder med
//       95 % KI (Wald på differansen; gruppene er disjunkte og uavhengige);
//   (c) risikoratioen ved samme horisonter (log-transformert KI);
//   (d) khikvadrat- og Newcombe-kontrasten på as-of-andelen, til sammenlikning;
//   (e) den årsaksspesifikke logrank-testen, som svarer på et annet spørsmål.
//
// READ-ONLY. Ingen databasetilgang. Kjøres:
//   node sporringer/rev2-03-gray-og-risikodifferanse.mjs

import { lesKohort, aalenJohansen, ajF, ajVar, ajKI, risikoVed, grayTest, grayRutenett,
         newcombe, fisherEksakt, logrankStratifisert, normCdf, pTosidigZ,
         skrivJson, pst, r2, r3, r4, KJORT, KORPUSSLUTT, VINDU, H12, H18, H24 } from "./rev2-00-lib.mjs";

const Z = 1.959963984540054;
const HOR = [{ navn: "12 mnd", d: H12 }, { navn: "18 mnd", d: H18 }, { navn: "24 mnd", d: H24 }];

function kjor(randregel) {
  const D = lesKohort(randregel);
  const B = D.filter((r) => r.bygg), O = D.filter((r) => !r.bygg);
  const ajB = aalenJohansen(B), ajO = aalenJohansen(O);

  // (a) Grays test
  const rut = grayRutenett(D);
  const gray = grayTest(B, O, rut);

  // (b)+(c) risikodifferanse og -ratio per horisont
  const kontraster = HOR.map((h) => {
    const fB = ajF(ajB, h.d), fO = ajF(ajO, h.d);
    const vB = ajVar(ajB, h.d), vO = ajVar(ajO, h.d);
    const rd = fB - fO, seRd = Math.sqrt(vB + vO);
    const rr = fB / fO;
    // log-RR: Var[log RR] = Var(fB)/fB² + Var(fO)/fO²
    const seLogRr = Math.sqrt(vB / (fB * fB) + vO / (fO * fO));
    return {
      horisont: h.navn, dager: h.d,
      cif_bygg_pst: pst(fB, 2), cif_ovrige_pst: pst(fO, 2),
      ki_bygg_pst: ajKI(ajB, h.d).slice(0, 2).map((x) => pst(x, 2)),
      ki_ovrige_pst: ajKI(ajO, h.d).slice(0, 2).map((x) => pst(x, 2)),
      risikodifferanse_pp: pst(rd, 2),
      rd_se_pp: pst(seRd, 3),
      rd_ki95_pp: [pst(rd - Z * seRd, 2), pst(rd + Z * seRd, 2)],
      rd_z: r3(rd / seRd),
      rd_p: pTosidigZ(rd / seRd).toExponential(2),
      risikoratio: r4(rr),
      rr_ki95: [r4(Math.exp(Math.log(rr) - Z * seLogRr)), r4(Math.exp(Math.log(rr) + Z * seLogRr))],
      risikomengde_bygg: risikoVed(B, h.d),
      risikomengde_ovrige: risikoVed(O, h.d),
    };
  });

  // (d) as-of-kontrasten (den manuskriptet har i dag)
  const kB = B.filter((r) => r.innstilt).length, kO = O.filter((r) => r.innstilt).length;
  const a = kB, b = B.length - kB, c = kO, d2 = O.length - kO;
  const n = B.length + O.length;
  const khiYates = (n * Math.pow(Math.abs(a * d2 - b * c) - n / 2, 2)) /
    ((a + b) * (c + d2) * (a + c) * (b + d2));
  const [nlo, nhi] = newcombe(kB, B.length, kO, O.length);

  // (e) årsaksspesifikk logrank, ustratifisert og krets-stratifisert
  const lrU = logrankStratifisert(D, (r) => r.bygg, () => "alle");
  const lrS = logrankStratifisert(D, (r) => r.bygg, (r) => r.tingrett);

  return { D, B, O, gray, kontraster, asof: {
      bygg: [kB, B.length], ovrige: [kO, O.length],
      andel_bygg_pst: pst(kB / B.length, 2), andel_ovrige_pst: pst(kO / O.length, 2),
      differanse_pp: pst(kB / B.length - kO / O.length, 2),
      newcombe95_pp: [pst(nlo, 2), pst(nhi, 2)],
      khikvadrat_yates: r3(khiYates),
      p_khikvadrat: (1 - normCdf(Math.sqrt(khiYates))) * 2,
      p_fisher: fisherEksakt(a, b, c, d2),
    }, lrU, lrS };
}

console.log("«Tomme bo» — revisjon 2, steg 3: Grays test og risikodifferanse\n");

const P = kjor("sensurert");
const G = kjor("tidligst");

console.log("(a) GRAYS TEST — likhet mellom kumulativ-insidens-kurvene, bygg mot øvrige");
console.log(`    U = ${r3(P.gray.U)}  V = ${r3(P.gray.V)}  z = ${r3(P.gray.z)}`
  + `  χ²(1) = ${r3(P.gray.z * P.gray.z)}  p = ${P.gray.p.toExponential(3)}`);
console.log(`    grenseregel «tidligst»: z = ${r3(G.gray.z)}, p = ${G.gray.p.toExponential(3)}\n`);

console.log("(b) RISIKODIFFERANSE bygg − øvrige, kumulativ insidens ved fast horisont");
for (const k of P.kontraster)
  console.log(`    ${k.horisont}: ${k.cif_bygg_pst} % mot ${k.cif_ovrige_pst} %`
    + `  →  ${k.risikodifferanse_pp} pp  KI [${k.rd_ki95_pp.join(", ")}]`
    + `  (z = ${k.rd_z}, p = ${k.rd_p});  RR ${k.risikoratio} [${k.rr_ki95.join(", ")}]`
    + `  risikomengde ${k.risikomengde_bygg}/${k.risikomengde_ovrige}`);

console.log("\n(d) TIL SAMMENLIKNING — as-of-kontrasten (manuskriptets nåværende hovedtest)");
console.log(`    ${P.asof.andel_bygg_pst} % mot ${P.asof.andel_ovrige_pst} %`
  + `  →  ${P.asof.differanse_pp} pp  Newcombe-KI [${P.asof.newcombe95_pp.join(", ")}]`
  + `  χ²(Yates) = ${P.asof.khikvadrat_yates}, Fisher p = ${P.asof.p_fisher.toExponential(2)}`);
console.log(`    (randregel «tidligst» = talljournalens telling: ${G.asof.andel_bygg_pst} % mot`
  + ` ${G.asof.andel_ovrige_pst} %, ${G.asof.differanse_pp} pp,`
  + ` χ²(Yates) = ${G.asof.khikvadrat_yates})`);

console.log("\n(e) ÅRSAKSSPESIFIKK LOGRANK — et annet spørsmål (rate blant fortsatt uavgjorte)");
console.log(`    ustratifisert:      z = ${r3(P.lrU.z)}, HR = ${r3(P.lrU.hr)}`
  + ` [${r3(P.lrU.hr_lav)}, ${r3(P.lrU.hr_hoy)}], p = ${P.lrU.p.toExponential(2)}`);
console.log(`    stratifisert krets: z = ${r3(P.lrS.z)}, HR = ${r3(P.lrS.hr)}`
  + ` [${r3(P.lrS.hr_lav)}, ${r3(P.lrS.hr_hoy)}], p = ${P.lrS.p.toExponential(2)}`);

const ut = {
  studie: "Tomme bo — revisjon 2 etter fagfellevurdering",
  leverer: "fagfellens punkt 6 — Grays test og direkte kumulativ-insidens-kontrast som primær gruppesammenlikning",
  skript: "sporringer/rev2-03-gray-og-risikodifferanse.mjs",
  kjort: KJORT,
  datagrunnlag: "offentlig tilgjengelige registerkunngjøringer om konkursbehandling",
  frosset_uttrekk: "data/_kohort-rader-arbeidskopi.json",
  kohortvindu: VINDU,
  sensureringsdato: KORPUSSLUTT,
  metode: {
    grays_test: "Gray (1988), ρ = 0. Logrank-type test på subdistribusjonsrisikomengden "
      + "R_g(t) = Y_g(t)·(1 − F̂_1g(t−))/Ŝ_g(t−), estimert i hver gruppe for seg. "
      + "Tester H0: CIF_bygg(t) = CIF_øvrige(t) for alle t.",
    risikodifferanse: "CIF_bygg(t) − CIF_øvrige(t) ved fast horisont. Varians = summen av de to "
      + "Aalen–Johansen-variansene (disjunkte, uavhengige grupper); 95 % KI på Wald-form.",
    risikoratio: "CIF_bygg(t)/CIF_øvrige(t); KI på log-skala med deltametoden.",
    aarsaksspesifikk_logrank: "hendelse = § 135; ordinær avslutning behandlet som sensurering. "
      + "HR er Peto/ett-stegs-estimatoren exp((O−E)/V) med KI exp((O−E)/V ± 1,96/√V). "
      + "Den svarer på et ANNET spørsmål enn Grays test: raten blant bo som fortsatt er uavgjorte.",
    randregel_primaer: "sensurert", randregel_grense: "tidligst",
  },
  primaer: {
    grays_test: { U: r3(P.gray.U), V: r3(P.gray.V), z: r3(P.gray.z),
      khikvadrat_1df: r3(P.gray.z * P.gray.z), p: P.gray.p },
    kontraster_fast_horisont: P.kontraster,
    asof_kontrast_til_sammenlikning: P.asof,
    aarsaksspesifikk_logrank: {
      ustratifisert: { z: r3(P.lrU.z), hr: r3(P.lrU.hr), hr_ki95: [r3(P.lrU.hr_lav), r3(P.lrU.hr_hoy)],
        p: P.lrU.p, O: P.lrU.O, E: r2(P.lrU.E), V: r2(P.lrU.V) },
      stratifisert_rettskrets: { strata: P.lrS.strata, z: r3(P.lrS.z), hr: r3(P.lrS.hr),
        hr_ki95: [r3(P.lrS.hr_lav), r3(P.lrS.hr_hoy)], p: P.lrS.p,
        O: P.lrS.O, E: r2(P.lrS.E), V: r2(P.lrS.V), hendelsestider: P.lrS.hendelsestider },
    },
  },
  grense_randregel_tidligst: {
    grays_test: { z: r3(G.gray.z), p: G.gray.p },
    kontraster_fast_horisont: G.kontraster,
    asof_kontrast: G.asof,
  },
  merknad_tolkning: "Grays test og den årsaksspesifikke logrank-testen kan peke i samme retning uten å "
    + "være samme test. Grays test sammenlikner ANDELEN som er innstilt innen dag t; den "
    + "årsaksspesifikke logrank-testen sammenlikner RATEN blant dem som fortsatt er uavgjorte. "
    + "Rapporter hvilken som er primær, og bland dem aldri i én setning.",
};
skrivJson(`data/rev2-03-gray-og-risikodifferanse-${KJORT}.json`, ut);
