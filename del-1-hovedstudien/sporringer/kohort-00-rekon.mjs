// LANE 1 / kohort — rekognosering (READ-ONLY).
// Formål: bekrefte skjema, korpusgrenser og serieoppstart før kohorten fryses.
// Kjør: node kohort-00-rekon.mjs
import { getPool, closePool } from "./db.mjs";

const pool = getPool();
const out = (label, rows) => {
  console.log("\n=== " + label + " ===");
  console.log(JSON.stringify(rows, null, 1));
};

try {
  await pool.query("set statement_timeout = '900s'");

  out("kolonner i kunngjoring.insolvens", (await pool.query(`
    select column_name, data_type
    from information_schema.columns
    where table_schema='kunngjoring' and table_name='insolvens'
    order by ordinal_position
  `)).rows);

  out("indekser paa kunngjoring.insolvens", (await pool.query(`
    select indexname, indexdef from pg_indexes
    where schemaname='kunngjoring' and tablename='insolvens'
  `)).rows);

  out("indekser paa kunngjoring.kunngjoring", (await pool.query(`
    select indexname, indexdef from pg_indexes
    where schemaname='kunngjoring' and tablename='kunngjoring'
  `)).rows);

  out("typer i insolvens (rader/selskaper/vindu)", (await pool.query(`
    select type,
           count(*) as rader,
           count(distinct orgnr) as selskaper,
           min(dato) as forste,
           max(dato) as siste
    from kunngjoring.insolvens
    group by type
    order by count(distinct orgnr) desc
  `)).rows);

  out("korpusets ytterkanter (kunngjoring)", (await pool.query(`
    select min(dato) as forste, max(dato) as siste from kunngjoring.insolvens
  `)).rows);
} catch (e) {
  console.error("FEIL:", e.message);
} finally {
  await closePool();
}
