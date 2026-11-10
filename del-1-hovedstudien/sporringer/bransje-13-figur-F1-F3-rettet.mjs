// bransje-13: retter F1 og F3.
//  F1  får kolonnen er_byggfag_kjerne, slik at eiendomsutvikling (SN2007 41.1),
//      som ligger i seksjon F i SN2007 men flyttes ut i SN2025, kan skilles visuelt
//      uten å fjernes fra tabellen.
//  F3  bygges nå datadrevet fra selve kartet: for hver kanoniske SN2007-kode
//      listes de FAKTISK TRYKTE etikettene på hver side av sømmen med antall.
//      Første utgave brukte SSBs kodenavn og bommet på etiketter som Brønnøysund
//      skriver annerledes («Blikkenslagerarbeid på tak») eller som avkortes ved
//      60 tegn («Annen spesialisert bygge- og anleggsvirksomhet ikke nevnt an»).
// READ-ONLY.
import { q, done, writeCsv, writeJson, clopperPearson, RUN_DATE } from "./_lib.mjs";
import { readFileSync } from "node:fs";

const DATA = "./data";
const kartJson = JSON.parse(readFileSync(`${DATA}/bransjekart-v3_${RUN_DATE}.json`, "utf8"));
const kart = new Map(kartJson.kart.map((r) => [r.etikett.normalize("NFC"), r]));
const MIN_CELLE = 10;
const MODEN = { start: "2023-08-24", slutt: "2024-12-31" };

const KM = (await q(`
  with apn as materialized (
    select orgnr, min(dato) as forste_apning, max(nullif(trim(bransje),'')) as etikett
    from kunngjoring.insolvens where type = 'Konkurs - åpning' group by orgnr
  ),
  koh as materialized (
    select * from apn where forste_apning between date '${MODEN.start}' and date '${MODEN.slutt}'
  ),
  inn as materialized (select orgnr, min(dato) as dato from kunngjoring.insolvens
                       where type ilike 'Konkurs - innstilling%' group by orgnr),
  avs as materialized (select orgnr, min(dato) as dato from kunngjoring.insolvens
                       where type ilike 'Konkurs - avslutning%' group by orgnr)
  select k.etikett, i.dato is not null as innstilt, v2.dato is not null as avsluttet
  from koh k left join inn i on i.orgnr = k.orgnr left join avs v2 on v2.orgnr = k.orgnr
`)).rows;

// ---------------- F1 ----------------
const g = new Map();
for (const r of KM) {
  const k = r.etikett ? kart.get(r.etikett.normalize("NFC")) : null;
  if (!k?.er_bygg_F) continue;
  const key = `${k.kanonisk_sn2007}|${k.kanonisk_navn}|${k.er_bygg_kjerne}`;
  if (!g.has(key)) g.set(key, { n: 0, i: 0, a: 0, o: 0 });
  const b = g.get(key); b.n++;
  if (r.innstilt) b.i++; else if (r.avsluttet) b.a++; else b.o++;
}
const alle = [...g].map(([key, b]) => {
  const [kode, navn, kjerne] = key.split("|");
  const [lo, hi] = clopperPearson(b.i, b.n);
  return { kode, navn, kjerne: kjerne === "true", ...b, pst: (100 * b.i) / b.n, lo: 100 * lo, hi: 100 * hi };
}).sort((x, y) => y.pst - x.pst);

const publ = alle.filter((r) => r.n >= MIN_CELLE);
const und = alle.filter((r) => r.n < MIN_CELLE);
const uN = und.reduce((s, r) => s + r.n, 0), uI = und.reduce((s, r) => s + r.i, 0);
const [ulo, uhi] = clopperPearson(uI, uN);
const f1 = (x) => x.toFixed(1);

const F1 = writeCsv(`figurer/F1-byggfag-innstillingsandel_${RUN_DATE}.csv`,
  ["nace_sn2007", "naering", "er_byggfag_kjerne", "n_apnede_bo", "innstilt", "avsluttet", "fortsatt_apent",
   "innstilt_pst", "ki95_lav", "ki95_hoy"],
  [...publ.map((r) => [r.kode, r.navn, r.kjerne, r.n, r.i, r.a, r.o, f1(r.pst), f1(r.lo), f1(r.hi)]),
   ["(samlet)", `Byggnæringer med færre enn ${MIN_CELLE} bo (${und.length} næringer, slått sammen)`, "",
    uN, uI, und.reduce((s, r) => s + r.a, 0), und.reduce((s, r) => s + r.o, 0),
    f1((100 * uI) / uN), f1(100 * ulo), f1(100 * uhi)]]);

// ---------------- F3 ----------------
// per kanonisk SN2007-kode: trykte etiketter før og etter sømmen, med antall
const perKode = new Map();
for (const r of kartJson.kart) {
  if (!r.kanonisk_sn2007) continue;
  const bygg = r.er_bygg_F === true || /^(41|42|43|68\.12)/.test(r.kanonisk_sn2007);
  if (!bygg) continue;
  const key = `${r.kanonisk_sn2007}|${r.kanonisk_navn}`;
  if (!perKode.has(key)) perKode.set(key, { for: [], etter: [] });
  const b = perKode.get(key);
  if (r.selsk_for_som > 0) b.for.push({ etikett: r.etikett, n: r.selsk_for_som, kode: r.kode, std: r.standard });
  if (r.selsk_etter_som > 0) b.etter.push({ etikett: r.etikett, n: r.selsk_etter_som, kode: r.kode, std: r.standard });
}
// Personvern: alle publiserte antall følger samme grense som resten av pakken.
// Tall under 10 skrives «<10» — F3 skal vise HVILKE etiketter som skifter, ikke
// hvor mange foretak som står bak en enkelt liten etikett.
const skjul = (n) => (n > 0 && n < MIN_CELLE ? "<10" : n);
const F3rader = [...perKode].map(([key, b]) => {
  const [kode, navn] = key.split("|");
  // Flerbransje-etiketter bærer linjeskift i kilden; erstattes av « + » så CSV-en
  // ikke får innebygde linjeskift i en celle.
  const s = (a) => a.map((x) => `${x.etikett.replace(/\n/g, " + ")} (${skjul(x.n)})`).join(" ; ");
  const sum = (a) => a.reduce((t, x) => t + x.n, 0);
  const koderEtter = [...new Set(b.etter.map((x) => x.kode).filter(Boolean))].sort().join(" ");
  return { kode, navn,
    etiketter_for: s(b.for), n_for: sum(b.for),
    etiketter_etter: s(b.etter), n_etter: sum(b.etter),
    sn2025_koder: koderEtter,
    samme_etikett: b.for.length && b.etter.length &&
      b.for.map((x) => x.etikett).sort().join("|") === b.etter.map((x) => x.etikett).sort().join("|") };
}).sort((a, b) => (b.n_for + b.n_etter) - (a.n_for + a.n_etter));

const F3 = writeCsv(`figurer/F3-klassifikasjonssom_${RUN_DATE}.csv`,
  ["kanonisk_sn2007", "kanonisk_navn", "trykte_etiketter_for_2025_09_01", "selskaper_for",
   "trykte_etiketter_fra_2025_09_01", "selskaper_etter", "sn2025_koder", "etiketten_er_uendret"],
  F3rader.map((r) => [r.kode, r.navn, r.etiketter_for, skjul(r.n_for), r.etiketter_etter, skjul(r.n_etter),
    r.sn2025_koder, r.samme_etikett]));

// hvor mange byggnæringer bytter trykt etikett ved sømmen?
const bytter = F3rader.filter((r) => r.n_for > 0 && r.n_etter > 0 && !r.samme_etikett);
const forsvinner = F3rader.filter((r) => r.n_for > 0 && r.n_etter === 0);
const dukker_opp = F3rader.filter((r) => r.n_for === 0 && r.n_etter > 0);

const rapport = {
  kjoredato: RUN_DATE,
  F1, F3,
  byggnaeringer_i_kartet: F3rader.length,
  bytter_etikett_ved_sommen: bytter.map((r) => `${r.kode} ${r.navn}: «${r.etiketter_for}» -> «${r.etiketter_etter}»`),
  forsvinner_ved_sommen: forsvinner.map((r) => `${r.kode} ${r.navn}: ${r.etiketter_for}`),
  dukker_opp_ved_sommen: dukker_opp.map((r) => `${r.kode} ${r.navn}: ${r.etiketter_etter}`),
  F1_publisert: publ.length, F1_undertrykt: und.length, F1_undertrykt_selskaper: uN,
};
writeJson(`data/bransje-F1-F3-rapport_${RUN_DATE}.json`, rapport);
console.log(JSON.stringify(rapport, null, 2));
await done();
