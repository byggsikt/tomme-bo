// LANE 3 — domstol. Steg 4: bransje-etikett -> NACE (bygg = 41/42/43).
// insolvens.bransje er kildens næringstekst, avkortet ved 60 tegn (L13-familien).
// Kobles mot left(company.industry_text_1,60). Dødt selskap har sjelden NACE selv
// (DØD-NACE-FELLEN), derfor kobles ETIKETTEN, ikke selskapet.
// READ-ONLY (kun SELECT). Kjøres: node domstol-04-bransjekobling.mjs
import { getPool, closePool } from "./db.mjs";

const pool = getPool();
await pool.query("set statement_timeout = '900s'");

async function show(title, sql, params = []) {
  const t0 = Date.now();
  const r = await pool.query(sql, params);
  console.log(`\n=== ${title}  (${((Date.now() - t0) / 1000).toFixed(2)}s, ${r.rowCount} rader) ===`);
  console.table(r.rows);
  return r.rows;
}

// Etikett -> NACE-kode, avledet fra levende selskapers industry_text_1 (60 tegn).
const LABELMAP = `
etikett as materialized (
  select left(industry_text_1, 60) as etikett,
         min(industry_code_1)      as kode_min,
         max(industry_code_1)      as kode_max,
         count(*)                  as n
    from company_intel.company
   where nullif(trim(industry_text_1),'') is not null
     and nullif(trim(industry_code_1),'')  is not null
   group by 1
)`;

await show("A. Etiketter som peker på FLERE NACE-koder (tvetydighet)",
  `with ${LABELMAP}
   select count(*) filter (where kode_min = kode_max)  as entydige,
          count(*) filter (where kode_min <> kode_max) as tvetydige,
          count(*) as totalt
     from etikett`);

await show("B. Tvetydige etiketter — er de bygg? (topp 20)",
  `with ${LABELMAP}
   select etikett, kode_min, kode_max, n from etikett
    where kode_min <> kode_max order by n desc limit 20`);

const COHORT = `
with aapning as materialized (
  select orgnr, min(dato) as aapning_dato from kunngjoring.insolvens
   where type = 'Konkurs - åpning' group by orgnr),
kohort as materialized (
  select orgnr, aapning_dato from aapning
   where aapning_dato between date '2023-09-01' and date '2024-12-31'),
rad as materialized (
  select k.orgnr, k.aapning_dato,
         max(nullif(trim(i.bransje),'')) as bransje
    from kohort k join kunngjoring.insolvens i
      on i.orgnr=k.orgnr and i.dato=k.aapning_dato and i.type='Konkurs - åpning'
   group by 1,2),
${LABELMAP}`;

await show("C. Kohort: hvor mange bransje-etiketter finner en NACE?",
  `${COHORT}
   select count(*) as saker,
          count(e.etikett) as etikett_treff,
          count(*) - count(e.etikett) as uten_treff
     from rad r left join etikett e on e.etikett = r.bransje`);

await show("D. Kohort: bransje-etiketter UTEN NACE-treff (alle)",
  `${COHORT}
   select r.bransje, count(*) as saker
     from rad r left join etikett e on e.etikett = r.bransje
    where e.etikett is null group by 1 order by 2 desc`);

await show("E. Kohort: bygg (NACE 41/42/43) — antall og etiketter",
  `${COHORT}
   select left(e.kode_min,2) as nace2, e.kode_min as nace, r.bransje, count(*) as saker
     from rad r join etikett e on e.etikett = r.bransje
    where left(e.kode_min,2) in ('41','42','43')
    group by 1,2,3 order by saker desc`);

await show("F. Kohort: byggtotal (kontroll mot 1 142)",
  `${COHORT}
   select count(*) filter (where left(e.kode_min,2) in ('41','42','43')) as bygg,
          count(*) filter (where left(e.kode_min,2) not in ('41','42','43')) as ikke_bygg,
          count(*) filter (where e.kode_min is null) as ukjent,
          count(*) as totalt
     from rad r left join etikett e on e.etikett = r.bransje`);

await closePool();
