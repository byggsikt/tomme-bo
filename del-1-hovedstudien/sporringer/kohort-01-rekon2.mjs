// LANE 1 / kohort — rekognosering 2 (READ-ONLY).
// Datoer alltid som TEKST (to_char) — pg-driveren gjor date->JS Date i lokal tid og
// forskyver dagen ett dogn i JSON. Det er kilden til «2023-08-24 vs 2023-08-25».
import { getPool, closePool } from "./db.mjs";

const pool = getPool();
const out = (label, rows) => {
  console.log("\n=== " + label + " ===");
  console.log(JSON.stringify(rows, null, 1));
};

try {
  await pool.query("set statement_timeout = '900s'");

  out("er insolvens tabell eller view?", (await pool.query(`
    select c.relname, c.relkind, pg_size_pretty(pg_total_relation_size(c.oid)) as storrelse
    from pg_class c join pg_namespace n on n.oid=c.relnamespace
    where n.nspname='kunngjoring' and c.relname in ('insolvens','kunngjoring','v_hendelse')
  `)).rows);

  out("serieoppstart/-slutt som TEKST", (await pool.query(`
    select type,
           to_char(min(dato),'YYYY-MM-DD') as forste,
           to_char(max(dato),'YYYY-MM-DD') as siste,
           count(distinct orgnr) as selskaper
    from kunngjoring.insolvens
    where type in ('Konkurs - åpning',
                   'Konkurs - innstilling av bobehandlingen',
                   'Konkurs - avslutning av bobehandlingen',
                   'Fortsettelse av bobehandling')
    group by type order by 4 desc
  `)).rows);

  // Dekker insolvens-tabellen alle konkurs-radene i raatabellen?
  out("insolvens vs raatabell (Konkurs - aapning)", (await pool.query(`
    with raa as materialized (
      select distinct orgnr from kunngjoring.kunngjoring
      where type_kanon = 'Konkurs - åpning'
    ), ins as materialized (
      select distinct orgnr from kunngjoring.insolvens
      where type = 'Konkurs - åpning'
    )
    select (select count(*) from raa) as raa_selskaper,
           (select count(*) from ins) as insolvens_selskaper,
           (select count(*) from raa r where not exists (select 1 from ins i where i.orgnr=r.orgnr)) as kun_i_raa,
           (select count(*) from ins i where not exists (select 1 from raa r where r.orgnr=i.orgnr)) as kun_i_insolvens
  `)).rows);

  out("type_kanon-varianter som starter med 'Konkurs'", (await pool.query(`
    select type_kanon, count(*) as rader, count(distinct orgnr) as selskaper,
           to_char(min(dato),'YYYY-MM-DD') as forste, to_char(max(dato),'YYYY-MM-DD') as siste
    from kunngjoring.kunngjoring
    where type_kanon ilike 'Konkurs%'
    group by type_kanon order by 3 desc limit 30
  `)).rows);

  out("bransje-etiketter i konkursaapninger 2023+ (topp 30)", (await pool.query(`
    select nullif(trim(bransje),'') as bransje, count(distinct orgnr) as selskaper,
           to_char(min(dato),'YYYY-MM-DD') as forste, to_char(max(dato),'YYYY-MM-DD') as siste
    from kunngjoring.insolvens
    where type='Konkurs - åpning' and dato >= date '2023-01-01'
    group by 1 order by 2 desc nulls last limit 30
  `)).rows);

  out("antall distinkte bransje-etiketter, for/etter L17-sommen", (await pool.query(`
    select case when dato < date '2025-09-01' then 'SN2007 (< 2025-09-01)' else 'SN2025 (>= 2025-09-01)' end as vintage,
           count(distinct nullif(trim(bransje),'')) as etiketter,
           count(distinct orgnr) as selskaper
    from kunngjoring.insolvens
    where type='Konkurs - åpning'
    group by 1 order by 1
  `)).rows);

  out("tingrett-verdier i vinduet (topp 40)", (await pool.query(`
    select nullif(trim(tingrett),'') as tingrett, count(distinct orgnr) as selskaper
    from kunngjoring.insolvens
    where type='Konkurs - åpning' and dato between date '2023-09-01' and date '2024-12-31'
    group by 1 order by 2 desc nulls last limit 40
  `)).rows);
} catch (e) {
  console.error("FEIL:", e.message);
} finally {
  await closePool();
}
