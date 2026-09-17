// TALLREVISOR (finpuss 1) — uavhengige stikkprøver mot databasen. KUN SELECT.
// Uavhengig SQL-form: utfall beregnes I databasen med FILTER (where dato >= aapning),
// ikke i JS som kontroll-01. Kjør: node revisor-01-stikkprover.mjs
import { getPool, closePool } from "./db.mjs";

const FRA = "2023-09-01", TIL = "2024-12-31", SLUTT = "2026-08-24";
const pool = getPool();
const out = (k, v) => { console.log("\n=== " + k + " ==="); console.log(JSON.stringify(v, null, 1)); };

try {
  await pool.query("set statement_timeout = '900s'");

  // A. Kohort + fingeravtrykk + kanonisk utfall (første utfallskunngjøring PÅ/ETTER åpning)
  const a = (await pool.query(`
    with aap as materialized (
      select orgnr, min(dato) filter (where type = 'Konkurs - åpning') as aapning
      from kunngjoring.insolvens
      where type in ('Konkurs - åpning','Konkurs - innstilling av bobehandlingen',
                     'Konkurs - avslutning av bobehandlingen','Fortsettelse av bobehandling')
      group by orgnr
    ),
    koh as materialized (
      select orgnr, aapning from aap
      where aapning between date '${FRA}' and date '${TIL}'
    ),
    utf as materialized (
      select k.orgnr, k.aapning,
             min(i.dato) filter (where i.type = 'Konkurs - innstilling av bobehandlingen' and i.dato >= k.aapning) as innst_etter,
             min(i.dato) filter (where i.type = 'Konkurs - avslutning av bobehandlingen'  and i.dato >= k.aapning) as avsl_etter,
             min(i.dato) filter (where i.type = 'Konkurs - innstilling av bobehandlingen' and i.dato <  k.aapning) as innst_foer,
             min(i.dato) filter (where i.type = 'Fortsettelse av bobehandling') as forts
      from koh k
      left join kunngjoring.insolvens i on i.orgnr = k.orgnr
      group by k.orgnr, k.aapning
    )
    select
      count(*)::int as kohort,
      (select encode(sha256(convert_to(string_agg(orgnr, ',' order by orgnr),'UTF8')),'hex') from koh) as fingeravtrykk,
      count(*) filter (where innst_etter is not null)::int as innstilt_paa_etter,
      count(*) filter (where avsl_etter  is not null)::int as avsluttet_uansett,
      count(*) filter (where innst_etter is not null and avsl_etter is not null)::int as begge,
      count(*) filter (where innst_etter is not null and avsl_etter is not null and avsl_etter <  innst_etter)::int as begge_avsl_foerst,
      count(*) filter (where innst_etter is not null and avsl_etter is not null and avsl_etter =  innst_etter)::int as begge_samme_dag,
      count(*) filter (where innst_etter is null and avsl_etter is null)::int as fortsatt_apne,
      count(*) filter (where innst_foer is not null)::int as innst_foer_aapning,
      count(*) filter (where forts is not null)::int as med_fortsettelse,
      min(date '${SLUTT}' - aapning)::int as oppf_min,
      percentile_cont(0.5) within group (order by (date '${SLUTT}' - aapning))::numeric(10,1) as oppf_median,
      max(date '${SLUTT}' - aapning)::int as oppf_maks,
      min(aapning - innst_foer)::int as foer_gap_min,
      max(aapning - innst_foer)::int as foer_gap_maks
    from utf`)).rows[0];
  out("A_kohort_utfall_kanonisk", a);

  // B. Bransjeetikettens lengde på åpningsraden (avkortingspåstanden «60 tegn»)
  const b = (await pool.query(`
    with aap as materialized (
      select orgnr, min(dato) filter (where type = 'Konkurs - åpning') as aapning
      from kunngjoring.insolvens where type = 'Konkurs - åpning' group by orgnr
    ),
    koh as materialized (
      select orgnr, aapning from aap where aapning between date '${FRA}' and date '${TIL}'
    )
    select max(length(i.bransje))::int as maks_lengde,
           count(*) filter (where length(i.bransje) = 60)::int as antall_paa_60,
           count(*) filter (where length(i.bransje) > 60)::int as antall_over_60,
           count(*)::int as aapningsrader
    from koh k join kunngjoring.insolvens i
      on i.orgnr = k.orgnr and i.dato = k.aapning and i.type = 'Konkurs - åpning'`)).rows[0];
  out("B_bransjelengde", b);

  // C. Serie-førstedatoer (som tekst)
  const c = (await pool.query(`
    select type, to_char(min(dato),'YYYY-MM-DD') as forste, count(distinct orgnr)::int as selskaper
    from kunngjoring.insolvens
    where type in ('Konkurs - innstilling av bobehandlingen','Konkurs - avslutning av bobehandlingen')
    group by type order by type`)).rows;
  out("C_seriestarter", c);
} finally {
  await closePool();
}
