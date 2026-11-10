// LANE 3 — domstol. Steg 0: skjema-rekognosering (READ-ONLY).
// Hva finnes i kunngjoring.insolvens, hvordan ser tingrett/saksnr ut?
// Kjøres: node domstol-00-skjema.mjs
import { getPool, closePool } from "./db.mjs";

const pool = getPool();

async function show(title, sql, params = []) {
  const t0 = Date.now();
  const r = await pool.query(sql, params);
  console.log(`\n=== ${title}  (${((Date.now() - t0) / 1000).toFixed(2)}s, ${r.rowCount} rader) ===`);
  console.table(r.rows);
  return r.rows;
}

await pool.query("set statement_timeout = '900s'");

await show(
  "A. Kolonner i kunngjoring.insolvens",
  `select column_name, data_type, is_nullable
     from information_schema.columns
    where table_schema = 'kunngjoring' and table_name = 'insolvens'
    order by ordinal_position`
);

await show(
  "B. Indekser på kunngjoring.insolvens",
  `select indexname, indexdef from pg_indexes
    where schemaname = 'kunngjoring' and tablename = 'insolvens'`
);

await show(
  "C. Radtyper i insolvens (topp 25)",
  `select type, count(*) as rader, count(distinct orgnr) as selskaper,
          count(nullif(trim(tingrett),'')) as har_tingrett,
          count(nullif(trim(saksnr),''))   as har_saksnr,
          count(nullif(trim(bransje),''))  as har_bransje,
          min(dato) as fra, max(dato) as til
     from kunngjoring.insolvens
    group by type
    order by rader desc
    limit 25`
);

await show(
  "D. saksnr — eksempler fra Konkurs - åpning",
  `select saksnr, tingrett, dato
     from kunngjoring.insolvens
    where type = 'Konkurs - åpning' and nullif(trim(saksnr),'') is not null
    order by random()
    limit 20`
);

await show(
  "E. saksnr — lengde/format-fordeling på konkursåpninger",
  `select length(trim(saksnr)) as len, count(*) as n,
          min(trim(saksnr)) as eksempel_min, max(trim(saksnr)) as eksempel_max
     from kunngjoring.insolvens
    where type = 'Konkurs - åpning' and nullif(trim(saksnr),'') is not null
    group by 1 order by n desc limit 20`
);

await closePool();
