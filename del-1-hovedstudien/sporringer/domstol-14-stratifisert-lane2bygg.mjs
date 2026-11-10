// LANE 3 — domstol. Steg 14: den tingretts-stratifiserte re-estimeringen kjørt
// på LANE 2s autoritative bransjekart (SSB Klass SN2007/SN2025-korrespondanse),
// ikke på min egen etikettmatch. Svaret skal ikke henge på hvilken byggdefinisjon
// som brukes — her vises det på alle fire.
// READ-ONLY. Kjøres: node domstol-14-stratifisert-lane2bygg.mjs
import { readFileSync, writeFileSync } from "node:fs";
import { createHash } from "node:crypto";
import { getPool, closePool } from "./db.mjs";
import { quantileSorted, kaplanMeier, kmQuantile, stratifiedLogrank, standardisedKM } from "./domstol-stat.mjs";

const ROOT = "./del-1-hovedstudien";
const KJORT = new Date().toISOString().slice(0, 10);

const kart = JSON.parse(readFileSync(`${ROOT}/data/bransjekart-v3_2026-08-30.json`, "utf8"));
const flagg = new Map(kart.kart.map((e) => [e.etikett, e]));
console.log(`Lane 2 bransjekart v3: ${kart.kart.length} etiketter, som_dato ${kart.som_dato}`);

const pool = getPool();
await pool.query("set statement_timeout='900s'");
const KODE = (c) => `nullif(regexp_replace(coalesce(substring(upper(trim(${c})) from 'KON-+([A-Z0-9]+)'),''),'KJENNELSE.*$',''),'')`;

const { rows: [{ korpusslutt }] } = await pool.query(
  `select to_char(max(dato),'YYYY-MM-DD') as korpusslutt from kunngjoring.insolvens`);

const { rows } = await pool.query(`
with aapning as materialized (
  select orgnr, min(dato) as aapning_dato from kunngjoring.insolvens
   where type='Konkurs - åpning' group by orgnr),
kohort as materialized (
  select orgnr, aapning_dato from aapning
   where aapning_dato between date '2023-09-01' and date '2024-12-31'),
aap as materialized (
  select k.orgnr, k.aapning_dato, max(nullif(trim(i.tingrett),'')) as navn,
         max(${KODE("i.saksnr")}) as kode, max(nullif(trim(i.bransje),'')) as bransje
    from kohort k join kunngjoring.insolvens i
      on i.orgnr=k.orgnr and i.dato=k.aapning_dato and i.type='Konkurs - åpning' group by 1,2),
innst as materialized (
  select k.orgnr, min(i.dato) as dt from kohort k join kunngjoring.insolvens i on i.orgnr=k.orgnr
   where i.type='Konkurs - innstilling av bobehandlingen' group by 1),
avsl as materialized (
  select k.orgnr, min(i.dato) as dt from kohort k join kunngjoring.insolvens i on i.orgnr=k.orgnr
   where i.type='Konkurs - avslutning av bobehandlingen' group by 1)
select a.navn, a.kode, a.bransje, to_char(a.aapning_dato,'YYYY-MM-DD') as aapning,
       to_char(i.dt,'YYYY-MM-DD') as innstilling, to_char(v.dt,'YYYY-MM-DD') as avslutning
  from aap a left join innst i on i.orgnr=a.orgnr left join avsl v on v.orgnr=a.orgnr`);

const DAY = 86400000, d = (s) => (s ? Date.parse(s + "T00:00:00Z") : null), slutt = d(korpusslutt);
for (const r of rows) {
  const e = flagg.get(r.bransje);
  r.bygg_kjerne = !!(e && e.er_bygg_kjerne);   // utførende bygg 41.2/41.0 + 42 + 43
  r.bygg_F      = !!(e && e.er_bygg_F);        // hele SN2007-område F
  r.dager = r.innstilling ? Math.round((d(r.innstilling) - d(r.aapning)) / DAY) : null;
  if (r.innstilling) { r.t = r.dager; r.event = 1; }
  else if (r.avslutning) { r.t = Math.round((d(r.avslutning) - d(r.aapning)) / DAY); r.event = 0; }
  else { r.t = Math.round((slutt - d(r.aapning)) / DAY); r.event = 0; }
  if (r.t < 0) r.t = 0;
}

function analyser(navn, felt) {
  const a = rows.filter((r) => r[felt]), b = rows.filter((r) => !r[felt]);
  const strata = new Map();
  for (const r of rows) {
    const k = r.kode || `NAVN:${r.navn}`;
    if (!strata.has(k)) strata.set(k, { a: [], b: [] });
    (r[felt] ? strata.get(k).a : strata.get(k).b).push({ t: r.t, event: r.event });
  }
  const lrU = stratifiedLogrank(new Map([["alle", {
    a: a.map((r) => ({ t: r.t, event: r.event })), b: b.map((r) => ({ t: r.t, event: r.event })) }]]));
  const lrS = stratifiedLogrank(strata);
  const raa = (arr) => quantileSorted(arr.filter((r) => r.innstilling).map((r) => r.dager).sort((x, y) => x - y), 0.5);
  const kmA = kaplanMeier(a.map((r) => ({ t: r.t, event: r.event })));
  const kmB = kaplanMeier(b.map((r) => ({ t: r.t, event: r.event })));
  const stdB = standardisedKM(strata, "a", "b");
  const medStd = (c) => { for (let i = 0; i < c.times.length; i++) if (c.surv[i] <= 0.5) return c.times[i]; return NaN; };
  // byggvektet snitt av innen-krets medianforskjeller
  let wsum = 0, dsum = 0, nk = 0;
  for (const [k, g] of strata) {
    const ka = rows.filter((r) => (r.kode || `NAVN:${r.navn}`) === k && r[felt] && r.innstilling).map((r) => r.dager).sort((x, y) => x - y);
    const kb = rows.filter((r) => (r.kode || `NAVN:${r.navn}`) === k && !r[felt] && r.innstilling).map((r) => r.dager).sort((x, y) => x - y);
    if (ka.length >= 5 && kb.length >= 5) { dsum += (quantileSorted(ka, 0.5) - quantileSorted(kb, 0.5)) * ka.length; wsum += ka.length; nk++; }
  }
  const res = {
    definisjon: navn, n_bygg: a.length, n_ovrige: b.length,
    raa_median_bygg: raa(a), raa_median_ovrige: raa(b), raa_diff: raa(a) - raa(b),
    km_median_bygg: kmQuantile(kmA), km_median_ovrige: kmQuantile(kmB),
    km_median_ovrige_std_byggmiks: medStd(stdB),
    hr_ustratifisert: lrU.hr, hr_stratifisert: lrS.hr,
    z_stratifisert: lrS.z, p_stratifisert: lrS.p,
    innenkrets_vektet_diff_dager: dsum / wsum, antall_kretser_i_vekten: nk,
  };
  console.log(`\n--- ${navn} (bygg n=${a.length}) ---`);
  console.log(`  rå median (fullførte): bygg ${res.raa_median_bygg}  øvrige ${res.raa_median_ovrige}  diff ${res.raa_diff}`);
  console.log(`  KM-median: bygg ${res.km_median_bygg}  øvrige ${res.km_median_ovrige}` +
    `  øvrige standardisert til byggs domstolsmiks ${res.km_median_ovrige_std_byggmiks}`);
  console.log(`  HR ustratifisert ${res.hr_ustratifisert.toFixed(3)} -> stratifisert på krets ${res.hr_stratifisert.toFixed(3)}` +
    `  (z=${res.z_stratifisert.toFixed(2)}, p=${res.p_stratifisert.toExponential(2)})`);
  console.log(`  byggvektet innen-krets medianforskjell: +${res.innenkrets_vektet_diff_dager.toFixed(1)} dager (${nk} kretser)`);
  return res;
}

const res = [
  analyser("bygg_kjerne (lane 2: utførende bygg 41.2/41.0+42+43)", "bygg_kjerne"),
  analyser("bygg_F (lane 2: hele SN2007-område F)", "bygg_F"),
];

const cols = Object.keys(res[0]);
const t = `# Byggsikt — «Tomme bo», lane 3. Tingretts-stratifisert re-estimering av
# byggs varighetsgap, kjørt ${KJORT} på lane 2s bransjekart v3 (SSB Klass).
# Kohort: konkursåpning 2023-09-01..2024-12-31, n=${rows.length}. Sensurering ${korpusslutt}.
# HR < 1 betyr at byggbo innstilles SAKTERE (lavere øyeblikkelig rate) enn øvrige.
# Sammenlikn hr_ustratifisert med hr_stratifisert: forskjellen ER domstolsmiksens bidrag.
` + cols.join("\t") + "\n" + res.map((r) => cols.map((c) => {
  const v = r[c];
  return typeof v === "number" && !Number.isInteger(v) ? v.toFixed(6) : String(v);
}).join("\t")).join("\n") + "\n";
writeFileSync(`${ROOT}/data/domstol-stratifisert-byggap.tsv`, t, "utf8");
console.log(`\nskrev data/domstol-stratifisert-byggap.tsv  sha256=${createHash("sha256").update(t, "utf8").digest("hex")}`);

await closePool();
