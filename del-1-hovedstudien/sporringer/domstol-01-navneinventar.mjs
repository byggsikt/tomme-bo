// LANE 3 — domstol. Steg 1: inventar over tingrettsnavn og saksnr-domstolskoder
// i kohortvinduet, samt bransjekobling (READ-ONLY, kun SELECT).
//
// Kohort: distinkte orgnr med type='Konkurs - åpning' og GLOBAL min(dato)
//         i 2023-09-01..2024-12-31 (L8/L14: alltid distinct orgnr).
// Kjøres: node domstol-01-navneinventar.mjs
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

// Felles kohort-CTE (MATERIALIZED — den korrelerte EXISTS-formen timet ut på 480 s).
const COHORT = `
with aapning as materialized (
  select orgnr, min(dato) as aapning_dato
    from kunngjoring.insolvens
   where type = 'Konkurs - åpning'
   group by orgnr
),
kohort as materialized (
  select orgnr, aapning_dato from aapning
   where aapning_dato >= date '2023-09-01' and aapning_dato <= date '2024-12-31'
),
aapningsrad as materialized (
  select k.orgnr, k.aapning_dato,
         max(nullif(trim(i.tingrett),'')) as tingrett,
         max(nullif(trim(i.saksnr),''))   as saksnr,
         max(nullif(trim(i.bransje),''))  as bransje
    from kohort k
    join kunngjoring.insolvens i
      on i.orgnr = k.orgnr and i.dato = k.aapning_dato and i.type = 'Konkurs - åpning'
   group by k.orgnr, k.aapning_dato
)`;

await show("A. Kohortstørrelse (kontroll mot 5 165)",
  `${COHORT}
   select count(*) as selskaper,
          count(tingrett) as har_tingrett,
          count(saksnr)   as har_saksnr,
          count(bransje)  as har_bransje,
          to_char(min(aapning_dato),'YYYY-MM-DD') as fra,
          to_char(max(aapning_dato),'YYYY-MM-DD') as til
     from aapningsrad`);

await show("B. Tingrettsnavn i kohorten (rå, alle)",
  `${COHORT}
   select tingrett, count(*) as saker,
          to_char(min(aapning_dato),'YYYY-MM-DD') as forste,
          to_char(max(aapning_dato),'YYYY-MM-DD') as siste
     from aapningsrad group by tingrett order by saker desc`);

await show("C. Domstolskode i saksnr (segment etter 'KON-' foran '/')",
  `${COHORT}
   select substring(saksnr from 'KON-?([A-Z0-9]+)') as kode, count(*) as saker
     from aapningsrad group by 1 order by saker desc`);

await show("D. Navn x kode — krysstabell (topp 60)",
  `${COHORT}
   select tingrett, substring(saksnr from 'KON-?([A-Z0-9]+)') as kode, count(*) as saker
     from aapningsrad group by 1,2 order by saker desc limit 60`);

await show("E. company-kolonner (bransjekobling)",
  `select column_name, data_type from information_schema.columns
    where table_schema='company_intel' and table_name='company'
      and (column_name ilike '%industry%' or column_name ilike '%nace%' or column_name ilike '%naering%')
    order by ordinal_position`);

await closePool();
