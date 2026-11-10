// bransje-00: skjemasonde. READ-ONLY.
// Hva finnes i kunngjoring.insolvens og company_intel.company som lane «bransje» trenger?
import { q, done } from "./_lib.mjs";

const out = {};

out.insolvens_kolonner = (await q(`
  select column_name, data_type
  from information_schema.columns
  where table_schema = 'kunngjoring' and table_name = 'insolvens'
  order by ordinal_position
`)).rows;

out.company_kolonner = (await q(`
  select column_name, data_type
  from information_schema.columns
  where table_schema = 'company_intel' and table_name = 'company'
    and (column_name ilike '%industry%' or column_name ilike '%nace%'
         or column_name in ('orgnr','is_deleted','sletting_dato','org_form','navn','name'))
  order by ordinal_position
`)).rows;

out.insolvens_typer = (await q(`
  select type, count(*) as rader, count(distinct orgnr) as selskaper,
         min(dato)::text as fra, max(dato)::text as til,
         count(nullif(trim(bransje),'')) as bransje_utfylt
  from kunngjoring.insolvens
  where type ilike 'Konkurs%'
  group by type
  order by rader desc
`)).rows;

out.bransje_lengder = (await q(`
  select length(trim(bransje)) as len, count(*) as rader
  from kunngjoring.insolvens
  where nullif(trim(bransje),'') is not null
  group by 1 order by 1 desc limit 12
`)).rows;

out.industry_kolonne_eksempel = (await q(`
  select industry_code_1, industry_text_1, length(industry_text_1) as len
  from company_intel.company
  where industry_text_1 is not null
  limit 5
`)).rows;

console.log(JSON.stringify(out, null, 2));
await done();
