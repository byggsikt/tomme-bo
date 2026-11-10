// LANE 3 — domstol. Steg 2: navnedrift over hele perioden + uenighet
// mellom navn og saksnr-kode, og mellom åpningsrad og innstillingsrad.
// READ-ONLY (kun SELECT).
// Kjøres: node domstol-02-navnedrift.mjs
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

// A. Alle tingrettsnavn i hele insolvens-tabellen, med kode og tidsspenn.
await show("A. Navn x kode, HELE perioden (rettshandlinger)",
  `select trim(tingrett) as tingrett,
          substring(trim(saksnr) from 'KON-?([A-Z0-9]+)') as kode,
          count(*) as rader,
          count(distinct orgnr) as selskaper,
          to_char(min(dato),'YYYY-MM-DD') as forste,
          to_char(max(dato),'YYYY-MM-DD') as siste
     from kunngjoring.insolvens
    where nullif(trim(tingrett),'') is not null
    group by 1,2 order by 1,3 desc`);

// B. Navn som deler kode (= navnedrift) — kjernen i domstolreform-sjekken.
await show("B. Koder med FLERE navn (navnedrift), hele perioden",
  `with x as (
     select trim(tingrett) as navn,
            substring(trim(saksnr) from 'KON-?([A-Z0-9]+)') as kode,
            dato
       from kunngjoring.insolvens
      where nullif(trim(tingrett),'') is not null
        and nullif(trim(saksnr),'') is not null
   )
   select kode, count(distinct navn) as antall_navn,
          string_agg(distinct navn, ' | ') as navn
     from x group by kode having count(distinct navn) > 1 order by 2 desc, 1`);

// C. Når skifter navnet? Per kode med drift, første/siste dato per navn.
await show("C. Tidsvindu per (kode, navn) for kodene med drift",
  `with x as (
     select trim(tingrett) as navn,
            substring(trim(saksnr) from 'KON-?([A-Z0-9]+)') as kode,
            dato
       from kunngjoring.insolvens
      where nullif(trim(tingrett),'') is not null
        and nullif(trim(saksnr),'') is not null
   ),
   drift as (select kode from x group by kode having count(distinct navn) > 1)
   select x.kode, x.navn, count(*) as rader,
          to_char(min(x.dato),'YYYY-MM-DD') as forste,
          to_char(max(x.dato),'YYYY-MM-DD') as siste
     from x join drift d using (kode)
    group by 1,2 order by 1, min(x.dato)`);

// D. Navn som opptrer med FLERE koder (motsatt retning).
await show("D. Navn med FLERE koder",
  `with x as (
     select trim(tingrett) as navn,
            substring(trim(saksnr) from 'KON-?([A-Z0-9]+)') as kode
       from kunngjoring.insolvens
      where nullif(trim(tingrett),'') is not null
        and nullif(trim(saksnr),'') is not null
   )
   select navn, count(distinct kode) as antall_koder,
          string_agg(distinct kode, ', ') as koder, count(*) as rader
     from x group by navn having count(distinct kode) > 1 order by 2 desc, 4 desc`);

// E. Kohorten: stemmer domstolen på åpningsraden med domstolen på innstillingsraden?
const COHORT = `
with aapning as materialized (
  select orgnr, min(dato) as aapning_dato from kunngjoring.insolvens
   where type = 'Konkurs - åpning' group by orgnr
),
kohort as materialized (
  select orgnr, aapning_dato from aapning
   where aapning_dato between date '2023-09-01' and date '2024-12-31'
),
aapningsrad as materialized (
  select k.orgnr, k.aapning_dato,
         max(nullif(trim(i.tingrett),'')) as a_navn,
         max(substring(trim(i.saksnr) from 'KON-?([A-Z0-9]+)')) as a_kode,
         max(nullif(trim(i.saksnr),'')) as a_saksnr
    from kohort k join kunngjoring.insolvens i
      on i.orgnr = k.orgnr and i.dato = k.aapning_dato and i.type = 'Konkurs - åpning'
   group by 1,2
),
innst as materialized (
  select k.orgnr, min(i.dato) as innst_dato
    from kohort k join kunngjoring.insolvens i on i.orgnr = k.orgnr
   where i.type = 'Konkurs - innstilling av bobehandlingen'
   group by k.orgnr
),
innstrad as materialized (
  select n.orgnr, n.innst_dato,
         max(nullif(trim(i.tingrett),'')) as i_navn,
         max(substring(trim(i.saksnr) from 'KON-?([A-Z0-9]+)')) as i_kode
    from innst n join kunngjoring.insolvens i
      on i.orgnr = n.orgnr and i.dato = n.innst_dato
     and i.type = 'Konkurs - innstilling av bobehandlingen'
   group by 1,2
)`;

await show("E1. Kohort: uenighetsrate navn-vs-kode på ÅPNINGSRADEN",
  `${COHORT}
   select count(*) as saker,
          count(a_kode) as har_kode,
          count(*) filter (where a_kode is null) as mangler_kode
     from aapningsrad`);

await show("E2. Kohort: åpningsdomstol vs innstillingsdomstol",
  `${COHORT}
   select count(*) as innstilte_saker,
          count(*) filter (where a_navn = i_navn) as samme_navn,
          count(*) filter (where a_navn <> i_navn) as ulikt_navn,
          count(*) filter (where a_kode = i_kode) as samme_kode,
          count(*) filter (where a_kode <> i_kode) as ulik_kode,
          count(*) filter (where i_kode is null or a_kode is null) as kode_mangler
     from aapningsrad a join innstrad i using (orgnr)`);

await show("E3. Kohort: hvilke navnepar er uenige (åpning -> innstilling)",
  `${COHORT}
   select a.a_navn as ved_aapning, i.i_navn as ved_innstilling,
          a.a_kode as kode_aapning, i.i_kode as kode_innstilling,
          count(*) as saker,
          to_char(min(i.innst_dato),'YYYY-MM-DD') as forste_innst,
          to_char(max(i.innst_dato),'YYYY-MM-DD') as siste_innst
     from aapningsrad a join innstrad i using (orgnr)
    where a.a_navn is distinct from i.i_navn or a.a_kode is distinct from i.i_kode
    group by 1,2,3,4 order by saker desc`);

await closePool();
