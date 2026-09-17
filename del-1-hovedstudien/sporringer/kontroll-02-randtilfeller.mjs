// DATAKONTROLLØREN — randtilfeller: kohortselskaper med utfallskunngjøring FØR
// første åpning i korpuset (tidligere konkursløp der åpningen er utgått hos kilden, L1).
// Avgjør om 3 897 (lanenes tall: innstilling uansett/etter åpning) eller 3 894
// (kun min(innstilling) >= åpning) er riktig. READ-ONLY. Kun aggregater skrives ut.
import { getPool, closePool } from "./db.mjs";

const pool = getPool();
try {
  await pool.query("set statement_timeout = '300s'");
  const r = (await pool.query(`
    with s as materialized (
      select orgnr,
             min(dato) filter (where type = 'Konkurs - åpning') as aapning,
             min(dato) filter (where type = 'Konkurs - innstilling av bobehandlingen') as innst_min,
             min(dato) filter (where type = 'Konkurs - avslutning av bobehandlingen') as avsl_min
      from kunngjoring.insolvens group by orgnr
    ),
    koh as materialized (
      select * from s where aapning between date '2023-09-01' and date '2024-12-31'
    ),
    kant as materialized (
      select * from koh where innst_min < aapning or avsl_min < aapning
    ),
    etter as materialized (
      select k.orgnr,
             min(i.dato) filter (where i.type = 'Konkurs - innstilling av bobehandlingen'
                                   and i.dato >= k.aapning) as innst_etter,
             min(i.dato) filter (where i.type = 'Konkurs - avslutning av bobehandlingen'
                                   and i.dato >= k.aapning) as avsl_etter
      from kant k join kunngjoring.insolvens i on i.orgnr = k.orgnr
      group by k.orgnr
    )
    select count(*) as kantselskaper,
           count(*) filter (where k.innst_min < k.aapning) as innst_foer,
           count(*) filter (where k.avsl_min < k.aapning) as avsl_foer,
           count(*) filter (where e.innst_etter is not null) as har_innstilling_etter_aapning,
           count(*) filter (where e.avsl_etter is not null) as har_avslutning_etter_aapning,
           count(*) filter (where e.innst_etter is null and e.avsl_etter is null) as uten_utfall_etter_aapning,
           min(k.aapning - k.innst_min) as minste_gap_dager,
           max(k.aapning - k.innst_min) as storste_gap_dager
    from kant k join etter e on e.orgnr = k.orgnr
  `)).rows[0];
  console.log(JSON.stringify(r, null, 1));

  // Hvilke grupper faller de i (aggregat, ingen orgnr): bransje-etikett-type og utfall etter åpning
  const g = (await pool.query(`
    with s as materialized (
      select orgnr,
             min(dato) filter (where type = 'Konkurs - åpning') as aapning,
             min(dato) filter (where type = 'Konkurs - innstilling av bobehandlingen') as innst_min,
             min(dato) filter (where type = 'Konkurs - avslutning av bobehandlingen') as avsl_min
      from kunngjoring.insolvens group by orgnr
    ),
    kant as materialized (
      select * from s where aapning between date '2023-09-01' and date '2024-12-31'
        and (innst_min < aapning or avsl_min < aapning)
    )
    select case when split_part(nullif(trim(i.bransje),''), e'\n', 1)
                     in ('Snekkerarbeid','Grunnarbeid','Malerarbeid','Elektrisk installasjonsarbeid',
                         'Oppføring av bygninger','Rørleggerarbeid','Annen spesialisert bygge- og anleggsvirksomhet',
                         'Takarbeid ellers','Blikkenslagerarbeid på tak','Glassarbeid','Grunnarbeid for vann og avløp')
                then 'byggfag-etikett'
                when split_part(nullif(trim(i.bransje),''), e'\n', 1) in ('Uoppgitt','Enheten er slettet')
                then 'uoppgitt'
                else 'annet' end as gruppe,
           count(*) as selskaper
    from kant k join kunngjoring.insolvens i
      on i.orgnr = k.orgnr and i.dato = k.aapning and i.type = 'Konkurs - åpning'
    group by 1 order by 2 desc
  `)).rows;
  console.log(JSON.stringify(g, null, 1));
} catch (e) { console.error("FEIL:", e.message); process.exitCode = 1; }
finally { await closePool(); }
