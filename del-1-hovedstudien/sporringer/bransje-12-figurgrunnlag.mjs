// bransje-12: figurgrunnlag og publiseringsuttrekk for lane «bransje».
//  F1  byggfag-stolpe med Clopper-Pearson-intervall (moden kohort), n >= 10
//  F2  rangering: byggfagene mot de største ikke-byggnæringene, n >= 10
//  F3  sømmen: etikettpar SN2007 <-> SN2025 med antall på hver side
//  F4  nedlastbart aggregat: næring x utfall x åpningskvartal, n >= 10, ellers undertrykt
// Ingen enkeltselskaper, ingen orgnr, ingen personer i noen av filene.
// READ-ONLY.
import { q, done, writeCsv, writeJson, clopperPearson, RUN_DATE } from "./_lib.mjs";
import { readFileSync } from "node:fs";

const DATA = "./data";
const kartJson = JSON.parse(readFileSync(`${DATA}/bransjekart-v3_${RUN_DATE}.json`, "utf8"));
const kart = new Map(kartJson.kart.map((r) => [r.etikett.normalize("NFC"), r]));
const MIN_CELLE = 10;

const HOVED = { start: "2023-09-01", slutt: "2024-12-31" };
const MODEN = { start: "2023-08-24", slutt: "2024-12-31" };

async function hentKohort(v) {
  return (await q(`
    with apn as materialized (
      select orgnr, min(dato) as forste_apning, max(nullif(trim(bransje),'')) as etikett
      from kunngjoring.insolvens where type = 'Konkurs - åpning' group by orgnr
    ),
    koh as materialized (
      select * from apn where forste_apning between date '${v.start}' and date '${v.slutt}'
    ),
    inn as materialized (
      select orgnr, min(dato) as dato from kunngjoring.insolvens
      where type ilike 'Konkurs - innstilling%' group by orgnr
    ),
    avs as materialized (
      select orgnr, min(dato) as dato from kunngjoring.insolvens
      where type ilike 'Konkurs - avslutning%' group by orgnr
    )
    select k.forste_apning::text as apning, k.etikett,
           i.dato is not null as innstilt, v2.dato is not null as avsluttet
    from koh k left join inn i on i.orgnr = k.orgnr left join avs v2 on v2.orgnr = k.orgnr
  `)).rows;
}
const KH = await hentKohort(HOVED);
const KM = await hentKohort(MODEN);

function bøtter(rader, nøkkel) {
  const g = new Map();
  for (const r of rader) {
    const k = r.etikett ? kart.get(r.etikett.normalize("NFC")) : null;
    const key = nøkkel(r, k);
    if (key === null || key === undefined) continue;
    if (!g.has(key)) g.set(key, { n: 0, innstilt: 0, avsluttet: 0, apen: 0, k });
    const b = g.get(key); b.n++;
    if (r.innstilt) b.innstilt++; else if (r.avsluttet) b.avsluttet++; else b.apen++;
  }
  return g;
}
function rader(g) {
  return [...g].map(([nokkel, b]) => {
    const [lo, hi] = clopperPearson(b.innstilt, b.n);
    return { nokkel, n: b.n, innstilt: b.innstilt, avsluttet: b.avsluttet, apen: b.apen,
      pst: (100 * b.innstilt) / b.n, lo: 100 * lo, hi: 100 * hi, k: b.k };
  });
}
const f1 = (x) => x.toFixed(1);

// ---------- F1: byggfagene ----------
const bygg = rader(bøtter(KM, (r, k) => (k?.er_bygg_F ? `${k.kanonisk_sn2007}|${k.kanonisk_navn}` : null)))
  .sort((a, b) => b.pst - a.pst);
const byggPubl = bygg.filter((r) => r.n >= MIN_CELLE);
const byggUnder = bygg.filter((r) => r.n < MIN_CELLE);
const underSum = byggUnder.reduce((s, r) => s + r.n, 0);
const underInns = byggUnder.reduce((s, r) => s + r.innstilt, 0);
const [ulo, uhi] = clopperPearson(underInns, underSum);

const F1 = writeCsv(`figurer/F1-byggfag-innstillingsandel_${RUN_DATE}.csv`,
  ["nace_sn2007", "naering", "n_apnede_bo", "innstilt", "avsluttet", "fortsatt_apent",
   "innstilt_pst", "ki95_lav", "ki95_hoy"],
  [...byggPubl.map((r) => {
      const [kode, navn] = r.nokkel.split("|");
      return [kode, navn, r.n, r.innstilt, r.avsluttet, r.apen, f1(r.pst), f1(r.lo), f1(r.hi)];
    }),
   ["(samlet)", `Byggfag med færre enn ${MIN_CELLE} bo (${byggUnder.length} næringer, slått sammen)`,
    underSum, underInns, byggUnder.reduce((s, r) => s + r.avsluttet, 0), byggUnder.reduce((s, r) => s + r.apen, 0),
    f1((100 * underInns) / underSum), f1(100 * ulo), f1(100 * uhi)]]);

// ---------- F2: rangering bygg mot ikke-bygg ----------
const alle5 = rader(bøtter(KH, (r, k) => {
  if (!k) return null;
  if (k.metode === "IKKE_NAERING") return "00.000|Ingen næring oppgitt i kunngjøringen";
  if (!k.kanonisk_sn2007) return null;
  return `${k.kanonisk_sn2007}|${k.kanonisk_navn}`;
}));
const F2rader = alle5.filter((r) => r.n >= MIN_CELLE).sort((a, b) => b.n - a.n);
const F2 = writeCsv(`figurer/F2-rangering-naeringer_${RUN_DATE}.csv`,
  ["nace_sn2007", "naering", "er_bygg_f", "n_apnede_bo", "innstilt", "avsluttet", "fortsatt_apent",
   "innstilt_pst", "ki95_lav", "ki95_hoy"],
  F2rader.map((r) => {
    const [kode, navn] = r.nokkel.split("|");
    return [kode, navn, r.k?.er_bygg_F === true, r.n, r.innstilt, r.avsluttet, r.apen, f1(r.pst), f1(r.lo), f1(r.hi)];
  }));

// ---------- F3: sømmen ----------
const somPar = [
  ["43.341", "Malerarbeid", "43.340", "Maler- og glassarbeid", "SN2025 slår sammen maler- og glassarbeid"],
  ["43.342", "Glassarbeid", "43.340", "Maler- og glassarbeid", "SN2025 slår sammen maler- og glassarbeid"],
  ["43.911", "Blikkenslagerarbeid", "43.410", "Takarbeid", "SN2025 slår blikkenslager og takarbeid sammen"],
  ["43.919", "Takarbeid ellers", "43.410", "Takarbeid", "SN2025 slår blikkenslager og takarbeid sammen"],
  ["41.109", "Utvikling og salg av egen fast eiendom ellers", "68.120", "Utvikling og salg av byggeprosjekter",
   "Flyttes UT av bygge- og anleggsvirksomhet (seksjon F) og inn i omsetning av fast eiendom (seksjon L)"],
  ["43.990", "Annen spesialisert bygge- og anleggsvirksomhet", "43.990",
   "Annen spesialisert bygge- og anleggsvirksomhet ikke nevnt annet sted", "Bare navnebytte"],
  ["43.110", "Riving av bygninger og andre konstruksjoner", "43.110", "Riving av bygninger og andre byggverk", "Bare navnebytte"],
  ["43.222", "Kuldeanlegg- og varmepumpearbeid", "43.222", "Kuldeanlegg-, varmepumpearbeid og installasjon av peiser", "Utvidet innhold"],
  ["43.320", "Snekkerarbeid", "43.320", "Snekkerarbeid", "Uendret"],
  ["43.120", "Grunnarbeid", "43.120", "Grunnarbeid", "Uendret"],
  ["43.221", "Rørleggerarbeid", "43.221", "Rørleggerarbeid", "Uendret"],
  ["43.210", "Elektrisk installasjonsarbeid", "43.210", "Elektrisk installasjonsarbeid", "Uendret"],
  ["41.200", "Oppføring av bygninger", "41.000", "Oppføring av bygninger", "Kodebytte, samme navn"],
];
const somTall = new Map();
for (const r of (await q(`
  select trim(bransje) as etikett,
         count(distinct orgnr) filter (where dato <  date '2025-09-01') as for_som,
         count(distinct orgnr) filter (where dato >= date '2025-09-01') as etter_som
  from kunngjoring.insolvens where type = 'Konkurs - åpning'
    and nullif(trim(bransje),'') is not null group by 1
`)).rows) somTall.set(r.etikett.normalize("NFC"), r);

const F3 = writeCsv(`figurer/F3-klassifikasjonssom_${RUN_DATE}.csv`,
  ["sn2007_kode", "sn2007_navn", "selskaper_med_sn2007_etikett_for_2025_09_01",
   "sn2025_kode", "sn2025_navn", "selskaper_med_sn2025_etikett_fra_2025_09_01", "endring"],
  somPar.map(([k7, n7, k5, n5, endring]) => [
    k7, n7, Number(somTall.get(n7.normalize("NFC"))?.for_som ?? 0),
    k5, n5, Number(somTall.get(n5.normalize("NFC"))?.etter_som ?? 0), endring]));

// ---------- F4: nedlastbart aggregat ----------
const kvartal = (d) => `${d.slice(0, 4)}K${Math.floor((Number(d.slice(5, 7)) - 1) / 3) + 1}`;
const agg = bøtter(KH, (r, k) => {
  if (!k) return null;
  const n = k.metode === "IKKE_NAERING" ? "00.000|Ingen næring oppgitt i kunngjøringen"
          : k.kanonisk_sn2007 ? `${k.kanonisk_sn2007}|${k.kanonisk_navn}` : null;
  return n ? `${n}|${kvartal(r.apning)}` : null;
});
const aggRader = rader(agg);
const publ = aggRader.filter((r) => r.n >= MIN_CELLE);
const undertrykt = aggRader.filter((r) => r.n < MIN_CELLE);
const F4 = writeCsv(`figurer/F4-aggregat-naering-kvartal_${RUN_DATE}.csv`,
  ["nace_sn2007", "naering", "aapningskvartal", "n_apnede_bo", "innstilt", "avsluttet", "fortsatt_apent", "innstilt_pst"],
  [...publ.sort((a, b) => b.n - a.n).map((r) => {
      const [kode, navn, kv] = r.nokkel.split("|");
      return [kode, navn, kv, r.n, r.innstilt, r.avsluttet, r.apen, f1(r.pst)];
    }),
   ["(undertrykt)", `Celler med færre enn ${MIN_CELLE} bo, slått sammen (${undertrykt.length} celler)`, "alle",
    undertrykt.reduce((s, r) => s + r.n, 0), undertrykt.reduce((s, r) => s + r.innstilt, 0),
    undertrykt.reduce((s, r) => s + r.avsluttet, 0), undertrykt.reduce((s, r) => s + r.apen, 0),
    f1((100 * undertrykt.reduce((s, r) => s + r.innstilt, 0)) / undertrykt.reduce((s, r) => s + r.n, 0))]]);

// ---------- bygg mot resten, med intervaller ----------
function del(rader, pred) {
  let n = 0, i = 0, a = 0, o = 0;
  for (const r of rader) {
    const k = r.etikett ? kart.get(r.etikett.normalize("NFC")) : null;
    if (!pred(k)) continue;
    n++; if (r.innstilt) i++; else if (r.avsluttet) a++; else o++;
  }
  const [lo, hi] = clopperPearson(i, n);
  return { n, innstilt: i, avsluttet: a, apen: o, pst: (100 * i) / n, ki: [100 * lo, 100 * hi],
           apen_pst: (100 * o) / n };
}
const sammenlikning = {
  vindu: HOVED,
  hele_kohorten: del(KH, () => true),
  bygg_F_41_42_43: del(KH, (k) => k?.er_bygg_F === true),
  bygg_kjerne_41_2_42_43: del(KH, (k) => k?.er_bygg_kjerne === true),
  eiendomsutvikling_41_1: del(KH, (k) => k?.er_eiendomsutvikling_41_1 === true),
  ovrige_naeringer: del(KH, (k) => k && k.er_bygg_F !== true && k.metode !== "IKKE_NAERING"),
  ingen_naering_oppgitt: del(KH, (k) => k?.metode === "IKKE_NAERING"),
};

const meta = writeJson(`data/bransje-metodegrunnlag_${RUN_DATE}.json`, {
  lane: "bransje",
  kjoredato: RUN_DATE,
  datagrunnlag: "Offentlig tilgjengelige registerkunngjøringer om konkurs (åpning, innstilling og avslutning av bobehandling).",
  kohortdefinisjon: {
    hendelse: "Kunngjort konkursåpning",
    identifikator: "Ett foretak = ett organisasjonsnummer; kohortdato = foretakets første kunngjorte konkursåpning",
    hovedvindu: HOVED, moden_kohort: MODEN,
    utfall: "Gjensidig utelukkende: innstilt / avsluttet / fortsatt åpent per uttrekksdato",
  },
  bransjetilordning: {
    kilde: "Næringen slik den er trykt i kunngjøringen om konkursåpning; avkortet ved 60 tegn i kilden",
    kart: `bransjekart-v3_${RUN_DATE}.csv`,
    kodeverk: kartJson.kilder,
    kanonisering: "Alle etiketter føres til femsifret SN2007-kode; etiketter fra SN2025 brytes tilbake via SSBs korrespondansetabell",
    som: "2025-09-01",
    andel_kanonisert_pst: kartJson.rapport.andel_kanonisert_pst,
    ikke_naering: kartJson.rapport.ikke_naering,
  },
  personvern: { minste_publiserte_celle: MIN_CELLE, ingen_foretak_eller_personer_navngis: true },
  konfidensintervall: "Clopper-Pearson eksakt binomisk 95 %",
  sammenlikning,
  filer: { F1: F1.path, F2: F2.path, F3: F3.path, F4: F4.path },
  sha256: { F1: F1.sha256, F2: F2.sha256, F3: F3.sha256, F4: F4.sha256 },
});

console.log(JSON.stringify({ F1, F2, F3, F4, meta, sammenlikning,
  byggfag_publisert: byggPubl.length, byggfag_undertrykt: byggUnder.length,
  aggregat_publisert: publ.length, aggregat_undertrykt: undertrykt.length }, null, 2));
await done();
