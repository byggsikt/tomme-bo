// LANE 3 — domstol. Steg 9: hva koster det å IKKE normalisere?
// Sammenlikner tre grupperinger av samme kohort:
//   (N1) navn på ÅPNINGSRADEN            <- vår metode
//   (N2) navn på UTFALLSRADEN            <- den naive
//   (N3) domstolskode fra saksnr          <- kryssjekken
// Og viser hva et umodent vindu gjør med spennet (høyresensurering).
// READ-ONLY. Kjøres: node domstol-09-normaliseringskostnad.mjs
import { getPool, closePool } from "./db.mjs";

const pool = getPool();
await pool.query("set statement_timeout = '900s'");

async function show(title, sql) {
  const t0 = Date.now();
  const r = await pool.query(sql);
  console.log(`\n=== ${title}  (${((Date.now() - t0) / 1000).toFixed(2)}s, ${r.rowCount} rader) ===`);
  console.table(r.rows);
  return r.rows;
}

const KODE = (c) => `nullif(regexp_replace(coalesce(substring(upper(trim(${c})) from 'KON-+([A-Z0-9]+)'),''),'KJENNELSE.*$',''),'')`;

const BASE = (fra, til) => `
with aapning as materialized (
  select orgnr, min(dato) as aapning_dato from kunngjoring.insolvens
   where type='Konkurs - åpning' group by orgnr),
kohort as materialized (
  select orgnr, aapning_dato from aapning
   where aapning_dato between date '${fra}' and date '${til}'),
aap as materialized (
  select k.orgnr, k.aapning_dato,
         max(nullif(trim(i.tingrett),'')) as a_navn, max(${KODE("i.saksnr")}) as a_kode
    from kohort k join kunngjoring.insolvens i
      on i.orgnr=k.orgnr and i.dato=k.aapning_dato and i.type='Konkurs - åpning' group by 1,2),
innst as materialized (
  select k.orgnr, min(i.dato) as innst_dato from kohort k
    join kunngjoring.insolvens i on i.orgnr=k.orgnr
   where i.type='Konkurs - innstilling av bobehandlingen' group by 1),
innstrad as materialized (
  select n.orgnr, n.innst_dato, max(nullif(trim(i.tingrett),'')) as i_navn
    from innst n join kunngjoring.insolvens i
      on i.orgnr=n.orgnr and i.dato=n.innst_dato
     and i.type='Konkurs - innstilling av bobehandlingen' group by 1,2),
sak as materialized (
  select a.orgnr, a.a_navn, a.a_kode, i.i_navn, i.innst_dato, a.aapning_dato,
         (i.innst_dato - a.aapning_dato) as dager
    from aap a left join innstrad i using (orgnr))`;

const MODEN = BASE("2023-09-01", "2024-12-31");

await show("N1. Gruppert på navn ved ÅPNING (vår metode), n>=100",
  `${MODEN}
   select a_navn as krets, count(*) as saker,
          count(innst_dato) as innstilt,
          round(100.0*count(innst_dato)/count(*),1) as andel_pst,
          percentile_cont(0.5) within group (order by dager) filter (where dager is not null) as median_dager
     from sak group by 1 having count(*) >= 100 order by andel_pst`);

await show("N2. Gruppert på navn ved INNSTILLING (naiv), n>=100 innstilte",
  `${MODEN}
   select i_navn as krets, count(*) as innstilte,
          percentile_cont(0.5) within group (order by dager) as median_dager
     from sak where i_navn is not null group by 1 order by innstilte desc`);

await show("N3. Gruppert på domstolskode fra saksnr, n>=100",
  `${MODEN}
   select a_kode as kode, count(*) as saker, count(innst_dato) as innstilt,
          round(100.0*count(innst_dato)/count(*),1) as andel_pst,
          percentile_cont(0.5) within group (order by dager) filter (where dager is not null) as median_dager
     from sak group by 1 having count(*) >= 100 order by andel_pst`);

// Høyresensurering: hva skjer med spennet når umodne åpninger tas med?
await show("S1. Umodent vindu 2023-09-01..2026-06-30 — spenn i innstillingsandel",
  `${BASE("2023-09-01", "2026-06-30")}
   select a_navn as krets, count(*) as saker, count(innst_dato) as innstilt,
          round(100.0*count(innst_dato)/count(*),1) as andel_pst
     from sak group by 1 having count(*) >= 100 order by andel_pst`);

await show("S2. Åpningskvartal x innstillingsandel (modningsbeviset)",
  `${BASE("2023-09-01", "2026-06-30")}
   select to_char(date_trunc('quarter', aapning_dato),'YYYY-"K"Q') as kvartal,
          count(*) as saker, count(innst_dato) as innstilt,
          round(100.0*count(innst_dato)/count(*),1) as andel_pst
     from sak group by 1 order by 1`);

await closePool();
