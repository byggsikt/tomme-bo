// LANE 3 — domstol. Steg 6: hvor mye bygg forsvinner i "ukjent"-bøtta?
// Eksakt etikettmatch (headline-definisjonen) vs toveis prefiksmatch som tåler
// SN2007->SN2025-sømmen (L17). READ-ONLY.
// Kjøres: node domstol-06-byggutvidet.mjs
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

// Kanoniske NACE-etiketter (nåværende vintage) fra company, alle tre slotter.
const NACE = `
nace as materialized (
  select trim(t) as tekst, min(trim(k)) as kode, count(*) as n
    from (
      select industry_text_1 t, industry_code_1 k from company_intel.company
      union all select industry_text_2, industry_code_2 from company_intel.company
      union all select industry_text_3, industry_code_3 from company_intel.company
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
etiketter as materialized (
  select bransje, count(*) as saker from rad where bransje is not null group by 1),
${NACE},
-- toveis prefiksmatch: kunngjøringsetiketten er kuttet ved 60 tegn, og
-- SN2007-navnet kan være både kortere og lengre enn SN2025-navnet.
match as materialized (
  select e.bransje, e.saker,
         min(n.kode) filter (where n.tekst = e.bransje)                              as kode_eksakt,
         min(n.kode) filter (where n.tekst like e.bransje || '%')                    as kode_prefiks_frem,
         min(n.kode) filter (where e.bransje like n.tekst || '%')                    as kode_prefiks_bak
    from etiketter e left join nace n
      on n.tekst = e.bransje or n.tekst like e.bransje || '%' or e.bransje like n.tekst || '%'
   group by 1,2
)`;

await show("A. Etikettdekning: eksakt vs prefiks",
  `${COHORT}
   select sum(saker) as saker_totalt,
          sum(saker) filter (where kode_eksakt is not null) as eksakt,
          sum(saker) filter (where kode_eksakt is null and coalesce(kode_prefiks_frem,kode_prefiks_bak) is not null) as kun_prefiks,
          sum(saker) filter (where coalesce(kode_eksakt,kode_prefiks_frem,kode_prefiks_bak) is null) as fortsatt_bom
     from match`);

await show("B. Bygg: eksakt (headline) vs utvidet",
  `${COHORT}
   select sum(saker) filter (where left(kode_eksakt,2) in ('41','42','43')) as bygg_eksakt,
          sum(saker) filter (where left(coalesce(kode_eksakt,kode_prefiks_frem,kode_prefiks_bak),2) in ('41','42','43')) as bygg_utvidet
     from match`);

await show("C. Bygg-etiketter som KUN prefiksmatch fanger (= tapt i headline)",
  `${COHORT}
   select bransje, saker, kode_prefiks_frem, kode_prefiks_bak
     from match
    where kode_eksakt is null
      and left(coalesce(kode_prefiks_frem,kode_prefiks_bak),2) in ('41','42','43')
    order by saker desc`);

await show("D. Alle bygg-etiketter i kohorten (eksakt-treff), med kode",
  `${COHORT}
   select bransje, saker, kode_eksakt
     from match where left(kode_eksakt,2) in ('41','42','43')
    order by saker desc`);

await show("E. Bom-etiketter som fortsatt ikke finner NACE (topp 25)",
  `${COHORT}
   select bransje, saker from match
    where coalesce(kode_eksakt,kode_prefiks_frem,kode_prefiks_bak) is null
    order by saker desc limit 25`);

await closePool();
