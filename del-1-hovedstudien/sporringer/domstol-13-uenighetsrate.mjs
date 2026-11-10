// LANE 3 — domstol. Steg 13: uenighetsraten navn-vs-kode i HELE korpuset,
// periodebevisst (før domstolreformen 2021-04-26 / mellom / etter delingen
// 2025-06-10), samt utfyllingen av tingrett/saksnr per radtype.
// READ-ONLY. Kjøres: node domstol-13-uenighetsrate.mjs
import { getPool, closePool } from "./db.mjs";

const pool = getPool();
await pool.query("set statement_timeout = '900s'");
const KODE = (c) => `nullif(regexp_replace(coalesce(substring(upper(trim(${c})) from 'KON-+([A-Z0-9]+)'),''),'KJENNELSE.*$',''),'')`;

async function show(title, sql) {
  const t0 = Date.now();
  const r = await pool.query(sql);
  console.log(`\n=== ${title}  (${((Date.now() - t0) / 1000).toFixed(2)}s, ${r.rowCount} rader) ===`);
  console.table(r.rows);
  return r.rows;
}

await show("A. Utfylling per radtype (count(nullif(trim(..),'')) — L5)",
  `select type,
          count(*) as rader,
          count(distinct orgnr) as selskaper,
          count(nullif(trim(tingrett),'')) as tingrett,
          count(nullif(trim(saksnr),''))   as saksnr,
          count(nullif(trim(bostyrer),'')) as bostyrer,
          count(nullif(trim(bransje),''))  as bransje
     from kunngjoring.insolvens
    where type in ('Konkurs - åpning','Konkurs - innstilling av bobehandlingen',
                   'Konkurs - avslutning av bobehandlingen','Fortsettelse av bobehandling',
                   'Tvangsoppløsning av aksjeselskap','Tvangsavvikling av aksjeselskap')
    group by 1 order by rader desc`);

await show("B. Periodebevisst uenighet navn-vs-kode, HELE korpuset",
  `with r as (
     select trim(tingrett) as navn, ${KODE("saksnr")} as kode, dato,
            case when dato <  date '2021-04-26' then '1 før reformen 2021'
                 when dato <  date '2025-06-10' then '2 23 rettskretser'
                 else                                '3 etter delingen 2025' end as periode
       from kunngjoring.insolvens
      where nullif(trim(tingrett),'') is not null and nullif(trim(saksnr),'') is not null),
   med_kode as (select * from r where kode is not null),
   dom as (
     select periode, kode, navn, count(*) as n,
            row_number() over (partition by periode, kode order by count(*) desc) as rn
       from med_kode group by 1,2,3)
   select m.periode,
          count(*) as rader,
          count(*) filter (where m.navn = d.navn) as stemmer_med_dominerende,
          count(*) filter (where m.navn <> d.navn) as avviker,
          round(100.0*count(*) filter (where m.navn <> d.navn)/count(*), 3) as avviksrate_pst
     from med_kode m join dom d on d.periode=m.periode and d.kode=m.kode and d.rn=1
    group by 1 order by 1`);

await show("C. Avvikene i periode 2 og 3 — hvilke navn",
  `with r as (
     select trim(tingrett) as navn, ${KODE("saksnr")} as kode, dato,
            case when dato <  date '2021-04-26' then '1 før reformen 2021'
                 when dato <  date '2025-06-10' then '2 23 rettskretser'
                 else                                '3 etter delingen 2025' end as periode
       from kunngjoring.insolvens
      where nullif(trim(tingrett),'') is not null and nullif(trim(saksnr),'') is not null),
   med_kode as (select * from r where kode is not null),
   dom as (select periode, kode, navn, count(*) as n,
                  row_number() over (partition by periode, kode order by count(*) desc) as rn
             from med_kode group by 1,2,3)
   select m.periode, m.kode, d.navn as dominerende, m.navn as avvikende, count(*) as rader,
          to_char(min(m.dato),'YYYY-MM-DD') as forste, to_char(max(m.dato),'YYYY-MM-DD') as siste
     from med_kode m join dom d on d.periode=m.periode and d.kode=m.kode and d.rn=1
    where m.navn <> d.navn and m.periode <> '1 før reformen 2021'
    group by 1,2,3,4 order by rader desc limit 25`);

await show("D. Rader der saksnr mangler kode (kan ikke kryssjekkes)",
  `select type, count(*) as rader
     from kunngjoring.insolvens
    where nullif(trim(saksnr),'') is not null and ${KODE("saksnr")} is null
    group by 1 order by 2 desc`);

await show("E. Antall distinkte kretser per periode (mot 23 / 28)",
  `select case when dato <  date '2021-04-26' then '1 før reformen 2021'
               when dato <  date '2025-06-10' then '2 23 rettskretser'
               else                                '3 etter delingen 2025' end as periode,
          count(distinct trim(tingrett)) as distinkte_navn,
          count(distinct ${KODE("saksnr")}) as distinkte_koder,
          to_char(min(dato),'YYYY-MM-DD') as fra, to_char(max(dato),'YYYY-MM-DD') as til
     from kunngjoring.insolvens
    where nullif(trim(tingrett),'') is not null
    group by 1 order by 1`);

await show("F. Avslutningsraden: kan domstolen gjenvinnes fra saksnr?",
  `select count(*) as avslutningsrader,
          count(nullif(trim(tingrett),'')) as har_tingrett,
          count(${KODE("saksnr")}) as har_kode_i_saksnr
     from kunngjoring.insolvens
    where type = 'Konkurs - avslutning av bobehandlingen'`);

await closePool();
