// bransje-02: hvilken klassifikasjonsvintage bærer company_intel.company.industry_text_1?
// Og hvor godt matcher left(industry_text_1,60) mot insolvens-etikettene?
// READ-ONLY.
import { q, done } from "./_lib.mjs";

const out = {};

// Testetiketter: par (SN2007-form, SN2025-form) observert i etikett-sensusen
out.vintage_test = (await q(`
  select t.probe, count(*) as company_rader, min(c.industry_code_1) as kode_min, max(c.industry_code_1) as kode_maks
  from (values
    ('Drift av restauranter og kafeer'),            -- SN2007-form
    ('Drift av restauranter'),                      -- SN2025-form
    ('Utleie av egen eller leid fast eiendom ellers'),
    ('Utleie av egen eller leid fast eiendom'),
    ('Malerarbeid'),
    ('Maler- og glassarbeid'),
    ('Utvikling og salg av egen fast eiendom ellers'),
    ('Utvikling og salg av byggeprosjekter'),
    ('Annen spesialisert bygge- og anleggsvirksomhet')
  ) as t(probe)
  left join company_intel.company c on left(c.industry_text_1, 60) = t.probe
  group by t.probe
  order by t.probe
`)).rows;

// Hvor mange av de 756 etikettene finner en NACE-kode via 60-tegns match?
out.matchgrad = (await q(`
  with etiketter as materialized (
    select trim(bransje) as etikett, count(distinct orgnr) as selskaper
    from kunngjoring.insolvens
    where type = 'Konkurs - åpning' and nullif(trim(bransje),'') is not null
    group by 1
  ),
  kodeliste as materialized (
    select left(industry_text_1, 60) as etikett60,
           industry_code_1 as kode,
           count(*) as n
    from company_intel.company
    where nullif(trim(industry_text_1),'') is not null
      and nullif(trim(industry_code_1),'') is not null
    group by 1,2
  ),
  best as (
    select e.etikett, e.selskaper, k.kode, k.n,
           row_number() over (partition by e.etikett order by k.n desc nulls last, k.kode) as rn,
           count(k.kode) over (partition by e.etikett) as antall_koder
    from etiketter e
    left join kodeliste k on k.etikett60 = e.etikett
  )
  select
    count(*) as etiketter_totalt,
    count(*) filter (where kode is not null) as etiketter_med_kode,
    count(*) filter (where kode is null) as etiketter_uten_kode,
    count(*) filter (where antall_koder > 1) as etiketter_flertydige,
    sum(selskaper) as selskaper_totalt,
    sum(selskaper) filter (where kode is not null) as selskaper_med_kode
  from best where rn = 1
`)).rows[0];

// Hvilke etiketter finner INGEN kode? (topp 40 etter selskaper)
out.uten_kode = (await q(`
  with etiketter as materialized (
    select trim(bransje) as etikett, count(distinct orgnr) as selskaper,
           min(dato)::text as forste, max(dato)::text as siste
    from kunngjoring.insolvens
    where type = 'Konkurs - åpning' and nullif(trim(bransje),'') is not null
    group by 1
  ),
  kodeliste as materialized (
    select distinct left(industry_text_1, 60) as etikett60
    from company_intel.company
    where nullif(trim(industry_text_1),'') is not null
      and nullif(trim(industry_code_1),'') is not null
  )
  select e.etikett, e.selskaper, e.forste, e.siste
  from etiketter e
  left join kodeliste k on k.etikett60 = e.etikett
  where k.etikett60 is null
  order by e.selskaper desc
  limit 40
`)).rows;

console.log(JSON.stringify(out, null, 2));
await done();
