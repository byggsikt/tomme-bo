// LANE 1 / kohort — rekognosering 4 (READ-ONLY): hvorfor bommer etikett-oppslaget?
import { getPool, closePool } from "./db.mjs";
const pool = getPool();
const out = (l, r) => { console.log("\n=== " + l + " ==="); console.log(JSON.stringify(r, null, 1)); };
try {
  await pool.query("set statement_timeout = '900s'");

  out("hvordan ser industry_text_1 ut? (topp 20)", (await pool.query(`
    select industry_code_1, industry_text_1, length(industry_text_1) as len, count(*) as n
    from company_intel.company
    where industry_text_1 is not null
    group by 1,2,3 order by 4 desc limit 20
  `)).rows);

  out("finnes 'Butikkhandel med klær' i selskapsuniverset?", (await pool.query(`
    select industry_code_1, industry_text_1, count(*) as n
    from company_intel.company
    where industry_text_1 ilike '%Butikkhandel med kl%'
    group by 1,2 order by 3 desc limit 10
  `)).rows);

  out("finnes 'Blikkenslagerarbeid' i selskapsuniverset?", (await pool.query(`
    select industry_code_1, industry_text_1, count(*) as n
    from company_intel.company
    where industry_text_1 ilike '%Blikkenslager%'
    group by 1,2 order by 3 desc limit 10
  `)).rows);

  out("bransje-etiketter med linjeskift (flere naeringer) i kohortvinduet", (await pool.query(`
    select count(distinct orgnr) filter (where bransje like '%' || chr(10) || '%') as med_linjeskift,
           count(distinct orgnr) as totalt
    from kunngjoring.insolvens
    where type='Konkurs - åpning' and dato between date '2023-09-01' and date '2024-12-31'
      and nullif(trim(bransje),'') is not null
  `)).rows);

  out("etikett-lengder i kohortvinduet", (await pool.query(`
    select length(nullif(trim(bransje),'')) as len, count(*) as n
    from kunngjoring.insolvens
    where type='Konkurs - åpning' and dato between date '2023-09-01' and date '2024-12-31'
    group by 1 order by 1 desc limit 12
  `)).rows);

  out("forste linje av etiketten: treff mot industry_text_1?", (await pool.query(`
    with etiketter as materialized (
      select distinct split_part(nullif(trim(bransje),''), chr(10), 1) as etikett
      from kunngjoring.insolvens
      where type='Konkurs - åpning' and nullif(trim(bransje),'') is not null
    ),
    univers as materialized (
      select distinct left(industry_text_1,60) as etikett from company_intel.company
      where industry_text_1 is not null and industry_code_1 is not null
    )
    select count(*) as etiketter, count(u.etikett) as med_treff
    from etiketter e left join univers u on u.etikett = e.etikett
  `)).rows);
} catch (e) { console.error("FEIL:", e.message); } finally { await closePool(); }
