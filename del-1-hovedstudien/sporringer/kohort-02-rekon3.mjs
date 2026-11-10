// LANE 1 / kohort — rekognosering 3 (READ-ONLY).
// Naeringskoder: hvordan bygger vi bransje-etikett -> NACE 41/42/43?
import { getPool, closePool } from "./db.mjs";

const pool = getPool();
const out = (label, rows) => {
  console.log("\n=== " + label + " ===");
  console.log(JSON.stringify(rows, null, 1));
};

try {
  await pool.query("set statement_timeout = '900s'");

  out("kolonner i company_intel.company (naering)", (await pool.query(`
    select column_name, data_type
    from information_schema.columns
    where table_schema='company_intel' and table_name='company'
      and (column_name ilike '%industr%' or column_name ilike '%nace%' or column_name ilike '%naering%'
           or column_name in ('orgnr','is_deleted','sletting_dato','konkurs_dato','org_form'))
    order by ordinal_position
  `)).rows);

  out("navnedrift i tingrett over hele konkurskorpuset", (await pool.query(`
    select nullif(trim(tingrett),'') as tingrett,
           count(distinct orgnr) as selskaper,
           to_char(min(dato),'YYYY-MM-DD') as forste,
           to_char(max(dato),'YYYY-MM-DD') as siste
    from kunngjoring.insolvens
    where type='Konkurs - åpning'
    group by 1 order by 2 desc nulls last
  `)).rows);

  out("saksnr-prefiks (domstolskode) — eksempler", (await pool.query(`
    select left(nullif(trim(saksnr),''), 6) as saksnr_prefiks, count(*) as rader
    from kunngjoring.insolvens
    where type='Konkurs - åpning' and dato between date '2023-09-01' and date '2024-12-31'
    group by 1 order by 2 desc limit 15
  `)).rows);
} catch (e) {
  console.error("FEIL:", e.message);
} finally {
  await closePool();
}
