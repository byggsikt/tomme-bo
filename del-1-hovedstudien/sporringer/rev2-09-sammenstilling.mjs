// «Tomme bo» — REVISJON 2, steg 9: SAMMENSTILLING.
//
// Samler alt statistikklanen leverer til revisjonen i én maskinlesbar fil:
//   - det nye primærestimatet,
//   - hvert tall som skal ERSTATTE eller SUPPLERE noe i manuskriptet, med metode
//     og skriptnavn,
//   - hvert nytt tall som ikke fantes før,
//   - hvert AVVIK mot talljournalen som forfatterne må ta stilling til,
//   - en vakt som asserterer at ingen av de låste kjernetallene har flyttet seg.
//
// READ-ONLY. Ingen databasetilgang. Kjøres SIST:
//   node sporringer/rev2-09-sammenstilling.mjs

import { readFileSync } from "node:fs";
import { lesKohort, skrivJson, pst, r1, r2, r3, r4, KJORT, KORPUSSLUTT, VINDU } from "./rev2-00-lib.mjs";

const ROOT = "./del-1-hovedstudien";
const les = (n) => JSON.parse(readFileSync(`${ROOT}/data/${n}-${KJORT}.json`, "utf8"));
const V = les("rev2-01-validering");
const CI = les("rev2-02-kumulativ-insidens");
const GR = les("rev2-03-gray-og-risikodifferanse");
const PR = les("rev2-04-presisjon-hr-og-ph");
const SE = les("rev2-05-differensiell-sensitivitet");
const DK = les("rev2-06-domstolskontraster");
const ST = les("rev2-07-standardisering");
const PE = les("rev2-08-permutasjon");

const h24 = (blokk, gruppe) => blokk[gruppe].horisonter.find((h) => h.dager === 730);
const P = CI.primaer_randregel_sensurert, T = CI.grense_randregel_tidligst;

// ---------------------------------------------------------------------------
// VAKT: de låste kjernetallene skal ikke ha flyttet seg
// ---------------------------------------------------------------------------
const D = lesKohort("tidligst");
const BY = D.filter((r) => r.bygg), OV = D.filter((r) => !r.bygg);
const vakt = [
  ["kohort", D.length, 5165],
  ["innstilt", D.filter((r) => r.innstilt).length, 3897],
  ["andel innstilt %", +pst(D.filter((r) => r.innstilt).length / D.length), 75.5],
  ["kun avsluttet", D.filter((r) => r.utfall === "avsluttet").length, 917],
  ["fortsatt åpne", D.filter((r) => r.utfall === "fortsatt_apen").length, 351],
  ["begge kunngjøringer", D.filter((r) => r.utfall === "begge").length, 6],
  ["bygg utførende", BY.length, 1280],
  ["bygg innstilt", BY.filter((r) => r.innstilt).length, 911],
  ["bygg andel %", +pst(BY.filter((r) => r.innstilt).length / BY.length), 71.2],
  ["øvrige", OV.length, 3885],
  ["øvrige innstilt", OV.filter((r) => r.innstilt).length, 2986],
  ["øvrige andel %", +pst(OV.filter((r) => r.innstilt).length / OV.length), 76.9],
].map(([navn, faktisk, laast]) => ({ navn, faktisk, laast, uendret: faktisk === laast }));
const brudd = vakt.filter((v) => !v.uendret);

console.log("«Tomme bo» — revisjon 2, steg 9: sammenstilling\n");
console.log("VAKT — låste kjernetall:");
for (const v of vakt) console.log(`  ${v.uendret ? "OK  " : "BRUDD"}  ${v.navn}: ${v.faktisk} (låst ${v.laast})`);
if (brudd.length) { console.error(`\nSTOPP: ${brudd.length} låst kjernetall har flyttet seg.`); process.exit(1); }

// ---------------------------------------------------------------------------
const nyttPrimaerestimat = {
  hva: "24-måneders kumulativ insidens for innstilling etter kkl. § 135, "
    + "med ordinær avslutning av bobehandlingen som konkurrerende hendelse (Aalen–Johansen)",
  hele_kohorten: { verdi_pst: h24(P, "alle").cif_innstilling_pst,
    ki95_pst: [h24(P, "alle").ki95_lav_pst, h24(P, "alle").ki95_hoy_pst],
    risikomengde_ved_730d: h24(P, "alle").risikomengde,
    grenseregel_tidligst_pst: h24(T, "alle").cif_innstilling_pst },
  bygg: { verdi_pst: h24(P, "bygg").cif_innstilling_pst,
    ki95_pst: [h24(P, "bygg").ki95_lav_pst, h24(P, "bygg").ki95_hoy_pst],
    risikomengde_ved_730d: h24(P, "bygg").risikomengde },
  ovrige: { verdi_pst: h24(P, "ovrige").cif_innstilling_pst,
    ki95_pst: [h24(P, "ovrige").ki95_lav_pst, h24(P, "ovrige").ki95_hoy_pst],
    risikomengde_ved_730d: h24(P, "ovrige").risikomengde },
  antakelsesfri_kontroll: {
    hva: "Blant de 3 772 boene med FULL 24-måneders oppfølging er andelen innstilt innen dag 730 "
      + "en ren binomisk andel uten sensurering. Den bekrefter Aalen–Johansen-estimatet.",
    alle: P.alle.komplett_oppfolging_delkohort.find((k) => k.dager === 730),
    bygg: P.bygg.komplett_oppfolging_delkohort.find((k) => k.dager === 730),
    ovrige: P.ovrige.komplett_oppfolging_delkohort.find((k) => k.dager === 730),
    merknad: "Disse tallene er nøyaktig talljournalens F1/F2 ved 24 måneder (74,5 % totalt; "
      + "70,0 mot 76,0 % for bygg og øvrige). F1/F2 er altså delkohort-estimatoren, ikke "
      + "Aalen–Johansen — det forklarer differansen mot 74,8 %, og begge er fasthorisont-tall.",
  },
  hva_75_5_er: "3 897/5 165 = 75,5 % er den OBSERVERTE kumulative andelen per " + KORPUSSLUTT
    + ", der oppfølgingstiden varierer fra 601 til 1 088 dager. Den skal beholdes som "
    + "hovedtall i overskrift og sammendrag, men merkes as-of, ikke som en "
    + "fasthorisont-sannsynlighet.",
};

const erstatninger = [
  { manuskriptet_sier: "primærresultatet er 75,5 % (3 897/5 165)",
    skal_bli: "75,5 % står, men merkes «observert kumulativ andel per 24. august 2026». "
      + "Fasthorisont-primærestimatet er 24-måneders kumulativ insidens "
      + h24(P, "alle").cif_innstilling_pst + " % [" + h24(P, "alle").ki95_lav_pst + "–"
      + h24(P, "alle").ki95_hoy_pst + "]",
    fagfellepunkt: 4, skript: "rev2-02-kumulativ-insidens.mjs" },

  { manuskriptet_sier: "differansen bygg mot øvrige testes med χ²(Yates) 16,5, p = 4,8 × 10⁻⁵ på as-of-andelen",
    skal_bli: "primær gruppesammenlikning er Grays test (z = " + GR.primaer.grays_test.z
      + ", χ²(1) = " + GR.primaer.grays_test.khikvadrat_1df + ", p = "
      + GR.primaer.grays_test.p.toExponential(2) + ") og risikodifferansen ved 24 måneder: "
      + GR.primaer.kontraster_fast_horisont[2].risikodifferanse_pp + " pp ["
      + GR.primaer.kontraster_fast_horisont[2].rd_ki95_pp.join(", ")
      + "]. χ²-testen kan stå som sekundær; de to gir praktisk talt samme differanse "
      + "(−5,70 mot −5,69 pp), noe som er verdt å si eksplisitt.",
    fagfellepunkt: 6, skript: "rev2-03-gray-og-risikodifferanse.mjs" },

  { manuskriptet_sier: "«forskjellen vokser til +38,4 dager når rettskretsen holdes fast»",
    skal_bli: PR.c_observerte_hendelsestider.korrekt_formulering
      + " De to tallene er ULIKE ESTIMANDER på ULIKE DELMENGDER, og det ene «vokser» ikke til det andre.",
    fagfellepunkt: 7, skript: "rev2-04-presisjon-hr-og-ph.mjs" },

  { manuskriptet_sier: "«ingen felles x kan snu rekkefølgen» presenteres som at reversering er umulig",
    skal_bli: SE.d_verste_tilfelle.paakrevd_formulering
      + " Vippepunktene: ved 0 % hos øvrige kreves "
      + SE.b_vippepunktkurve.ankerpunkter.ved_0_pst_i_ovrige.kreves_i_bygg_pst
      + " % hos bygg, ved 25 % kreves "
      + SE.b_vippepunktkurve.ankerpunkter.ved_25_pst_i_ovrige.kreves_i_bygg_pst
      + " %, og over " + SE.c_umulighetsgrense.grense_pst + " % hos øvrige er reversering umulig.",
    fagfellepunkt: 5, skript: "rev2-05-differensiell-sensitivitet.mjs" },

  { manuskriptet_sier: "«Næringsmiksen forklarer ingenting av domstolsvariasjonen.»",
    skal_bli: ST.konklusjon.paakrevd_formulering + " Tallfesting: " + ST.konklusjon.tallfesting,
    fagfellepunkt: 12, skript: "rev2-07-standardisering.mjs" },

  { manuskriptet_sier: "«én krets ligger signifikant lavere enn flere andre» uten multiplisitetskorreksjon",
    skal_bli: "Etter Holm-korreksjon over alle 120 parvise Fisher-tester overlever "
      + DK.b_parvise_holm.signifikante_etter_holm + " par, alle med Hordaland tingrett i den lave enden "
      + "(mot Møre og Romsdal, Oslo og Trøndelag). I den tilsvarende «én krets mot resten»-analysen "
      + "er Hordaland den eneste kretsen som skiller seg etter Holm (p_Holm = "
      + r4(DK.c_en_krets_mot_resten.tester[0].p_holm) + "). Påstanden holder — men den skal bæres av "
      + "de korrigerte testene, ikke av tellingen av ikke-overlappende intervaller.",
    fagfellepunkt: 13, skript: "rev2-06-domstolskontraster.mjs" },

  { manuskriptet_sier: "«permutasjonsvalidert med 300 omstokkinger; ingen nådde den observerte verdien»",
    skal_bli: PE.paakrevd_formulering,
    fagfellepunkt: "13 E", skript: "rev2-08-permutasjon.mjs" },

  { manuskriptet_sier: "«Byggebo har altså VEDVARENDE omtrent 20 prosent lavere øyeblikkelig rate»",
    skal_bli: "Ordet «vedvarende» må ut. Proporsjonalitetsantakelsen forkastes "
      + "(Grambsch–Therneau χ²(1) = " + PR.e_ph_diagnostikk.rang_transform.khikvadrat + ", p = "
      + PR.e_ph_diagnostikk.rang_transform.p.toExponential(2) + "). Den tidsdelte analysen viser at "
      + "hele forskjellen ligger i de første seks månedene: HR "
      + PR.e_ph_diagnostikk.tidsdelt_hr[0].hr + " [" + PR.e_ph_diagnostikk.tidsdelt_hr[0].ki95.join(", ")
      + "] i dag 0–180, deretter " + PR.e_ph_diagnostikk.tidsdelt_hr[1].hr + ", "
      + PR.e_ph_diagnostikk.tidsdelt_hr[2].hr + " og " + PR.e_ph_diagnostikk.tidsdelt_hr[3].hr
      + " i de tre påfølgende intervallene — alle med intervall som dekker 1. HR 0,80 er et "
      + "VEKTET GJENNOMSNITT over oppfølgingen, ikke en konstant rate.",
    fagfellepunkt: 14, skript: "rev2-04-presisjon-hr-og-ph.mjs" },

  { manuskriptet_sier: "domstolstabellens varighetsspenn 97–213 dager (median blant fullførte saker)",
    skal_bli: "Den sensureringsbevisste versjonen spenner "
      + DK.e_sensureringsbevisst_varighet.spenn.cif_median_dager.join("–")
      + " dager (CIF-median per krets). Medianen blant fullførte saker UNDERVURDERER spredningen "
      + "mellom kretsene fordi kretsene har ulik andel uavgjorte bo. Publiser begge, eller bytt.",
    fagfellepunkt: "13 D", skript: "rev2-06-domstolskontraster.mjs" },

  { manuskriptet_sier: "«z = −5,8; p ≈ 7 × 10⁻⁹» for den stratifiserte hasardratioen",
    skal_bli: "På den kanoniske byggdefinisjonen og det frosne kohortuttrekket er z = "
      + PR.d_hasardratio.peto_ett_stegs.z + " og p = "
      + PR.d_hasardratio.peto_ett_stegs.p.toExponential(2) + ". HR 0,80 reproduseres eksakt. "
      + "z = −5,8 stammer fra en eldre byggdefinisjon (domstol-08) og lar seg ikke reprodusere "
      + "under noen av de fire definisjons-/sensureringsvariantene, som alle gir z mellom −6,10 "
      + "og −6,44. To uavhengige implementasjoner gir identisk svar (differanse 0).",
    fagfellepunkt: 14, skript: "rev2-04-presisjon-hr-og-ph.mjs" },
];

const nyeTall = {
  kumulativ_insidens_12_18_24_mnd: {
    alle: P.alle.horisonter.map((h) => ({ horisont: h.horisont, cif_pst: h.cif_innstilling_pst,
      ki95_pst: [h.ki95_lav_pst, h.ki95_hoy_pst], risikomengde: h.risikomengde })),
    bygg: P.bygg.horisonter.map((h) => ({ horisont: h.horisont, cif_pst: h.cif_innstilling_pst,
      ki95_pst: [h.ki95_lav_pst, h.ki95_hoy_pst], risikomengde: h.risikomengde })),
    ovrige: P.ovrige.horisonter.map((h) => ({ horisont: h.horisont, cif_pst: h.cif_innstilling_pst,
      ki95_pst: [h.ki95_lav_pst, h.ki95_hoy_pst], risikomengde: h.risikomengde })),
  },
  grays_test: GR.primaer.grays_test,
  risikodifferanser: GR.primaer.kontraster_fast_horisont.map((k) => ({
    horisont: k.horisont, rd_pp: k.risikodifferanse_pp, ki95_pp: k.rd_ki95_pp,
    rr: k.risikoratio, rr_ki95: k.rr_ki95 })),
  cif_medianer_med_ki: {
    bygg: PR.a_cif_medianer.bygg, ovrige: PR.a_cif_medianer.ovrige,
    differanse: PR.b_differanse_kumulativ_insidens },
  hasardratio_med_ki: PR.d_hasardratio,
  ph_brudd: PR.e_ph_diagnostikk,
  differensielle_grenser: { vippepunkter: SE.b_vippepunktkurve.ankerpunkter,
    umulighetsgrense: SE.c_umulighetsgrense, verste_tilfelle: SE.d_verste_tilfelle,
    signifikansgrense: SE.e_statistisk_skillbarhet.ikke_lenger_signifikant_ved,
    empirisk_anker: SE.f_empirisk_anker.landemerker },
  domstolskontraster: { holm_par: DK.b_parvise_holm.overlevende_par,
    mot_resten: DK.c_en_krets_mot_resten.tester.filter((t) => t.p_holm < 0.2),
    hierarkisk: DK.d_hierarkisk_modell.tilpasning_16_kretser,
    krympede_estimater: DK.d_hierarkisk_modell.krympede_kretsestimater },
  standardisering: { stratatabell: ST.publiserbar_stratatabell,
    per_krets: ST.stratifiseringer.n2.kretser.map((k) => ({ krets: k.krets, saker: k.saker,
      O: k.O, E: r2(k.E), oe: r4(k.oe), oe_ki95: k.oe_ki95_binomisk.map((x) => r4(x)) })),
    heterogenitet: ST.stratifiseringer.n2.heterogenitet,
    hierarkisk_med_uten_offset: ST.stratifiseringer.n2.hierarkisk,
    robusthet_over_tre_stratifiseringer: Object.fromEntries(
      Object.entries(ST.stratifiseringer).map(([k, v]) => [k, {
        antall_strata: v.antall_strata, oe_spenn: v.spenn.observert_delt_paa_forventet,
        dempning_av_overskudd_pst: v.heterogenitet.dempning_av_overskudd_pst }])) },
  permutasjon: PE.stratifisert_logrank,
};

const avvik = [
  { hva: "talljournalens D5: +38,4 dager, 3 749 saker, «bygg tregest i 18 av 19 kretser»",
    funn: "Det frosne uttrekket gir +" + PR.c_observerte_hendelsestider.rettskrets_stratifisert.vektet_diff_dager
      + " dager, " + PR.c_observerte_hendelsestider.rettskrets_stratifisert.saker + " saker og 17 av 19.",
    aarsak: PR.c_observerte_hendelsestider.avvik_mot_talljournalens_D5.aarsak,
    anbefaling: PR.c_observerte_hendelsestider.avvik_mot_talljournalens_D5.konsekvens,
    alvorlighet: "lav — dekkes av bootstrap-KI ["
      + PR.c_observerte_hendelsestider.rettskrets_stratifisert.ki95_bootstrap.join(", ") + "] dager" },

  { hva: "talljournalens D4: «innstilt-andel ved ett år, bygg 57,2 %»",
    funn: "Det frosne uttrekket gir 57,11 % (primærregel) og 57,19 % (grenseregel).",
    aarsak: "De 3 randtilfellene. 57,2 % svarer til basens telling; 57,1 % til uttrekkets primærregel.",
    anbefaling: "Behold 57,2 %; oppgi randregelen i metodefila.", alvorlighet: "ubetydelig" },

  { hva: "talljournalens D6: «z = −5,8, p ≈ 7 × 10⁻⁹»",
    funn: "Kanonisk definisjon gir z = " + PR.d_hasardratio.peto_ett_stegs.z + ", p = "
      + PR.d_hasardratio.peto_ett_stegs.p.toExponential(2) + ". HR 0,80 er eksakt.",
    aarsak: "z = −5,8 er fra domstol-08 med den eldre byggdefinisjonen (1 142 bo). Ingen av de fire "
      + "kanoniske variantene gir −5,8. To uavhengige implementasjoner er enige om −6,13.",
    anbefaling: "Bytt z og p til de kanoniske verdiene, eller stryk z og p og oppgi bare HR med KI. "
      + "Merk at den lave presisjonen i lane 3s normalhale-approksimasjon uansett gjør «p ≈ 7 × 10⁻⁹» "
      + "upålitelig i siste siffer.",
    alvorlighet: "middels — et publisert tall som ikke reproduseres" },

  { hva: "manuskriptets E6/kapittel 9: standardisert spenn 0,888–1,085",
    funn: "Det frosne uttrekket gir " + ST.stratifiseringer.n2.spenn.observert_delt_paa_forventet.join("–") + ".",
    aarsak: "Lane 3 bygde næringsbøttene av en eksakt etikett→NACE-oppslagstabell i basen; "
      + "det frosne uttrekket bruker bransjekart-v3. Konklusjonen er den samme.",
    anbefaling: "Oppgi kilden til bøttene sammen med spennet.", alvorlighet: "lav" },

  { hva: "kontroll-05s join gir 5 166 rader, ikke 5 165",
    funn: "Ett foretak har to åpningsrader på samme dato og telles dobbelt i kontroll-05.",
    aarsak: "Joinen mot åpningskunngjøringen er ikke deduplisert på orgnr.",
    anbefaling: "Meldes til eierne. Påvirker kun kontroll-05s egne avledede tall (D5), ikke "
      + "kohortens kjernetall, som er bygget fra en deduplisert kohorttabell.",
    alvorlighet: "lav — men det er en reell defekt i et kontrollskript" },
];

const ut = {
  studie: "Tomme bo — revisjon 2 etter fagfellevurdering",
  rolle: "statistikklanen: fagfellens punkt 4, 5, 6, 7, 12, 14 og permutasjonsmerknaden",
  skript: "sporringer/rev2-09-sammenstilling.mjs",
  kjort: KJORT,
  datagrunnlag: "offentlig tilgjengelige registerkunngjøringer om konkursbehandling",
  frosset_uttrekk: "data/_kohort-rader-arbeidskopi.json",
  kohortvindu: VINDU, sensureringsdato: KORPUSSLUTT,
  alle_beregninger_kjort_paa: "det frosne kohortuttrekket, ikke databasen — samme kohort som resten av studien",
  vakt_laaste_kjernetall: { antall: vakt.length, brudd: brudd.length, sjekker: vakt },
  bibliotekvalidering: { skript: "rev2-01-validering.mjs", sjekker: V.antall_sjekker, feilende: V.feilende },
  nytt_primaerestimat: nyttPrimaerestimat,
  erstatninger,
  nye_tall: nyeTall,
  avvik_som_krever_beslutning: avvik,
  skript_og_filer: [
    { skript: "rev2-00-lib.mjs", rolle: "felles statistikkbibliotek (Aalen–Johansen, Grays test, "
      + "stratifisert logrank, Cox med Breslow-ties, Schoenfeld/PH, Clopper–Pearson, Newcombe, "
      + "Fisher eksakt, Holm, mulberry32)" },
    { skript: "rev2-01-validering.mjs", fil: "rev2-01-validering", rolle: "26 assertsjoner mot talljournalen" },
    { skript: "rev2-02-kumulativ-insidens.mjs", fil: "rev2-02-kumulativ-insidens", rolle: "punkt 4" },
    { skript: "rev2-03-gray-og-risikodifferanse.mjs", fil: "rev2-03-gray-og-risikodifferanse", rolle: "punkt 6" },
    { skript: "rev2-04-presisjon-hr-og-ph.mjs", fil: "rev2-04-presisjon-hr-og-ph", rolle: "punkt 7 og 14" },
    { skript: "rev2-05-differensiell-sensitivitet.mjs", fil: "rev2-05-differensiell-sensitivitet", rolle: "punkt 5" },
    { skript: "rev2-06-domstolskontraster.mjs", fil: "rev2-06-domstolskontraster", rolle: "punkt 13 A/B/D" },
    { skript: "rev2-07-standardisering.mjs", fil: "rev2-07-standardisering", rolle: "punkt 12" },
    { skript: "rev2-08-permutasjon.mjs", fil: "rev2-08-permutasjon", rolle: "punkt 13 E" },
  ],
  ikke_kjort: [
    "Fine–Gray-regresjon på underfordelingshasarden. Grays test og risikodifferansen dekker "
      + "kumulativ-insidens-sammenlikningen; manuskriptets § 13.8 skal fortsatt si at ingen "
      + "Fine–Gray-modell er kjørt.",
    "Cox-modell med flere kovariater samtidig (åpningskvartal, næring, domstol). § 13.8 står.",
    "Klynget bootstrap for de binomiske hovedandelene. Klynge-robust SE er beregnet for "
      + "hasardratioen (rettskrets som klynge) og utvider intervallet fra [0,734, 0,853] til "
      + "[0,724, 0,866] — det er indikasjonen på hvor mye klyngestrukturen betyr.",
  ],
};
skrivJson(`data/rev2-09-sammenstilling-${KJORT}.json`, ut);

console.log(`\n${erstatninger.length} erstatninger, ${avvik.length} avvik som krever beslutning.`);
console.log(`Nytt primærestimat: 24-mnd kumulativ insidens ${nyttPrimaerestimat.hele_kohorten.verdi_pst} %`
  + ` [${nyttPrimaerestimat.hele_kohorten.ki95_pst.join("–")}].`);
