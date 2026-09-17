// LANE 1 / kohort — rekognosering 5 (READ-ONLY): finnes en SN2007-ordbok noe sted?
// company.industry_text_1 er SN2025-vokabular; kunngjoringene 2023-24 er SN2007.
import { getPool, closePool } from "./db.mjs";
const pool = getPool();
const out = (l, r) => { console.log("\n=== " + l + " ==="); console.log(JSON.stringify(r, null, 1)); };
try {
  await pool.query("set statement_timeout = '900s'");

  out("alle kolonner som ligner naering/nace/bransje i hele basen", (await pool.query(`
    select table_schema, table_name, column_name, data_type
    from information_schema.columns
    where (column_name ilike '%industr%' or column_name ilike '%nace%'
           or column_name ilike '%naering%' or column_name ilike '%bransje%'
           or column_name ilike '%n_ring%')
      and table_schema not in ('information_schema','pg_catalog')
    order by table_schema, table_name, column_name
  `)).rows);

  out("feltnavn i kunngjoring.felt (topp 40)", (await pool.query(`
    select felt, count(*) as rader from kunngjoring.felt group by 1 order by 2 desc limit 40
  `)).rows);
} catch (e) { console.error("FEIL:", e.message); } finally { await closePool(); }
