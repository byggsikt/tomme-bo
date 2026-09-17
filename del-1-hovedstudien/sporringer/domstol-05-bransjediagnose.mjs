// LANE 3 — domstol. Steg 5: hvorfor bommer bransje-etiketten på NACE?
// Hypoteser: (a) trailing space etter 60-tegns kutt, (b) SN2007 vs SN2025-vintage
// (L17) — company er et NÅ-øyeblikksbilde, kunngjøringen er fra 2023/24.
// READ-ONLY. Kjøres: node domstol-05-bransjediagnose.mjs
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

await show("A. Finnes 'Drift av restauranter og kafeer' i company i det hele tatt?",
  `select 'text_1' as kol, industry_code_1 as kode, count(*) as n
     from company_intel.company where industry_text_1 ilike 'Drift av restauranter%'
    group by 1,2
   union all
   select 'text_2', industry_code_2, count(*) from company_intel.company
    where industry_text_2 ilike 'Drift av restauranter%' group by 1,2
   order by n desc limit 10`);

await show("B. Hva heter 56.101 i company NÅ?",
  `select industry_code_1 as kode, industry_text_1 as tekst, count(*) as n
     from company_intel.company where industry_code_1 like '56.10%'
    group by 1,2 order by n desc limit 10`);

await show("C. Bygg-koder i company NÅ (41/42/43) — etiketter",
  `select industry_code_1 as kode, industry_text_1 as tekst, count(*) as n
     from company_intel.company where left(industry_code_1,2) in ('41','42','43')
    group by 1,2 order by kode limit 60`);

// Utvidet etikettkilde: alle tre nærings-slotter.
const LABELMAP3 = `
etikett as materialized (
  select trim(left(t,60)) as etikett, min(k) as kode_min, max(k) as kode_max, count(*) as n
    from (
      select industry_text_1 as t, industry_code_1 as k from company_intel.company
      union all
      select industry_text_2, industry_code_2 from company_intel.company
      union all
      select industry_text_3, industry_code_3 from company_intel.company
    ) s
   where nullif(trim(t),'') is not null and nullif(trim(k),'') is not null
   group by 1
)`;

const COHORT = `
with aapning as materialized (
  select orgnr, min(dato) as aapning_dato from kunngjoring.insolvens
   where type='Konkurs - åpning' group by orgnr),
kohort as materialized (
  select orgnr, aapning_dato from aapning
   where aapning_dato between date '2023-09-01' and date '2024-12-31'),
rad as materialized (
  select k.orgnr, max(nullif(trim(i.bransje),'')) as bransje
    from kohort k join kunngjoring.insolvens i
      on i.orgnr=k.orgnr and i.dato=k.aapning_dato and i.type='Konkurs - åpning'
   group by 1),
${LABELMAP3}`;

await show("D. Kohort med TRIMMET 60-tegns etikett + alle tre slotter",
  `${COHORT}
   select count(*) as saker, count(e.etikett) as treff, count(*)-count(e.etikett) as bom
     from rad r left join etikett e on e.etikett = r.bransje`);

await show("E. Kohort: bygg-tall med utvidet kart (kontroll mot 1 142)",
  `${COHORT}
   select count(*) filter (where left(e.kode_min,2) in ('41','42','43')) as bygg,
          count(*) filter (where e.kode_min is not null and left(e.kode_min,2) not in ('41','42','43')) as ikke_bygg,
          count(*) filter (where e.kode_min is null) as ukjent, count(*) as totalt
     from rad r left join etikett e on e.etikett = r.bransje`);

await show("F. Kohort: gjenværende bom, topp 40",
  `${COHORT}
   select r.bransje, count(*) as saker
     from rad r left join etikett e on e.etikett = r.bransje
    where e.etikett is null group by 1 order by 2 desc limit 40`);

await closePool();
