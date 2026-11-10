// bransje-10b: som bransje-10, men rånivåtellingen filtrerer på den lagrede
// kolonnen type_kanon i stedet for å kalle kanoniser_type() i WHERE.
// Funksjonskallet i WHERE tvang full scan av 16,9 mill. rader (>600 s);
// type_kanon-formen svarer på sekunder. Notert som ytelseslandmine.
// READ-ONLY.
import { q, done, writeJson, RUN_DATE } from "./_lib.mjs";

const out = { kjoredato: RUN_DATE };

out.raa_vs_insolvens = (await q(`
  select 'kunngjoring.kunngjoring (type_kanon)' as tabell,
         count(*) as rader, count(distinct orgnr) as selskaper
  from kunngjoring.kunngjoring
  where type_kanon = 'Konkurs - åpning'
  union all
  select 'kunngjoring.insolvens', count(*), count(distinct orgnr)
  from kunngjoring.insolvens where type = 'Konkurs - åpning'
`)).rows;

out.insolvens_dublettnokkel = (await q(`
  select count(*) as par_orgnr_dato_med_flere_rader
  from (select orgnr, dato from kunngjoring.insolvens
        where type = 'Konkurs - åpning' group by orgnr, dato having count(*) > 1) t
`)).rows[0];

out.to_apningsrader = (await q(`
  with m as materialized (
    select orgnr from kunngjoring.insolvens
    where type = 'Konkurs - åpning' group by orgnr having count(*) > 1
  )
  select i.dato::text as dato, trim(i.bransje) as bransje,
         nullif(trim(i.tingrett),'') is not null as har_tingrett
  from kunngjoring.insolvens i join m on m.orgnr = i.orgnr
  where i.type = 'Konkurs - åpning' order by i.orgnr, i.dato
`)).rows;

// hvor mange orgnr har flere RÅ-rader, og har de samme bransje der?
out.raa_dubletter = (await q(`
  select count(*) as selskaper_med_flere_raarader
  from (select orgnr from kunngjoring.kunngjoring
        where type_kanon = 'Konkurs - åpning' group by orgnr having count(*) > 1) t
`)).rows[0];

out.som_effekt = (await q(`
  select trim(bransje) as etikett,
         count(distinct orgnr) filter (where dato <  date '2025-09-01') as for_som,
         count(distinct orgnr) filter (where dato >= date '2025-09-01') as etter_som,
         min(dato)::text as forste, max(dato)::text as siste
  from kunngjoring.insolvens
  where type = 'Konkurs - åpning'
    and trim(bransje) in (
      'Malerarbeid','Glassarbeid','Maler- og glassarbeid',
      'Annen spesialisert bygge- og anleggsvirksomhet',
      'Annen spesialisert bygge- og anleggsvirksomhet ikke nevnt annet sted',
      'Takarbeid ellers','Blikkenslagerarbeid på tak','Takarbeid',
      'Riving av bygninger og andre konstruksjoner','Riving av bygninger og andre byggverk',
      'Utvikling og salg av egen fast eiendom ellers','Utvikling og salg av byggeprosjekter',
      'Snekkerarbeid','Grunnarbeid','Rørleggerarbeid','Elektrisk installasjonsarbeid',
      'Oppføring av bygninger','Annet installasjonsarbeid',
      'Kuldeanlegg- og varmepumpearbeid','Kuldeanlegg-, varmepumpearbeid og installasjon av peiser',
      'Annen ferdiggjøring av bygninger','Installasjon av isoleringsmateriale',
      'Murerarbeid','Spesialisert byggevirksomhet i forbindelse med anleggsarbeid','VVS-arbeid'
    )
  group by 1 order by (count(distinct orgnr)) desc
`)).rows;

out.som_datoer = (await q(`
  with e as materialized (
    select trim(bransje) as etikett, dato from kunngjoring.insolvens where type = 'Konkurs - åpning'
  )
  select
    (select max(dato)::text from e where etikett = 'Drift av restauranter og kafeer') as siste_sn2007_restaurant,
    (select min(dato)::text from e where etikett = 'Drift av restauranter')            as forste_sn2025_restaurant,
    (select max(dato)::text from e where etikett = 'Malerarbeid')                      as siste_sn2007_maler,
    (select min(dato)::text from e where etikett = 'Maler- og glassarbeid')            as forste_sn2025_maler,
    (select max(dato)::text from e where etikett = 'Utvikling og salg av egen fast eiendom ellers') as siste_sn2007_eiendomsutv,
    (select min(dato)::text from e where etikett = 'Utvikling og salg av byggeprosjekter')          as forste_sn2025_eiendomsutv
`)).rows[0];

out.dod_nace_kohort = (await q(`
  with apn as materialized (
    select orgnr, min(dato) as forste from kunngjoring.insolvens
    where type = 'Konkurs - åpning' group by orgnr
  ),
  koh as materialized (
    select orgnr from apn where forste between date '2023-09-01' and date '2024-12-31'
  )
  select count(*) as kohort,
         count(*) filter (where c.is_deleted) as slettet,
         count(*) filter (where not c.is_deleted) as fortsatt_registrert,
         count(nullif(trim(c.industry_code_1),'')) as har_naeringskode,
         count(nullif(trim(c.industry_code_1),'')) filter (where c.is_deleted) as slettet_med_kode,
         count(nullif(trim(c.industry_code_1),'')) filter (where not c.is_deleted) as levende_med_kode
  from koh k join company_intel.company c on c.orgnr = k.orgnr
`)).rows[0];

const d = out.dod_nace_kohort;
out.dod_nace_avledet = {
  andel_slettet_pst: (100 * Number(d.slettet)) / Number(d.kohort),
  andel_med_naeringskode_pst: (100 * Number(d.har_naeringskode)) / Number(d.kohort),
  andel_slettede_uten_naeringskode_pst: (100 * (Number(d.slettet) - Number(d.slettet_med_kode))) / Number(d.slettet),
  andel_registrerte_med_naeringskode_pst: (100 * Number(d.levende_med_kode)) / Number(d.fortsatt_registrert),
  bransjeetikett_dekning_pst: null,
};

out.bransjedekning_kohort = (await q(`
  with apn as materialized (
    select orgnr, min(dato) as forste, max(nullif(trim(bransje),'')) as etikett
    from kunngjoring.insolvens where type = 'Konkurs - åpning' group by orgnr
  )
  select count(*) as kohort, count(etikett) as med_bransjeetikett,
         count(*) filter (where etikett = 'Uoppgitt') as uoppgitt
  from apn where forste between date '2023-09-01' and date '2024-12-31'
`)).rows[0];
out.dod_nace_avledet.bransjeetikett_dekning_pst =
  (100 * Number(out.bransjedekning_kohort.med_bransjeetikett)) / Number(out.bransjedekning_kohort.kohort);

writeJson(`data/bransje-stabilitet-og-som_${RUN_DATE}.json`, out);
console.log(JSON.stringify(out, null, 2));
await done();
