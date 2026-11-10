// LANE 3 — domstol. Steg 3: kodevarianter i saksnr og den ene uparsebare saken.
// READ-ONLY (kun SELECT).
// Kjøres: node domstol-03-kodevarianter.mjs
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

await show("A. Saksnr-mønstre som gir 'rare' koder (K-suffiks m.m.)",
  `select substring(trim(saksnr) from 'KON-?([A-Z0-9]+)') as kode,
          trim(tingrett) as navn,
          min(trim(saksnr)) as saksnr_min, max(trim(saksnr)) as saksnr_max,
          count(*) as rader,
          to_char(min(dato),'YYYY-MM-DD') as forste, to_char(max(dato),'YYYY-MM-DD') as siste
     from kunngjoring.insolvens
    where nullif(trim(saksnr),'') is not null and nullif(trim(tingrett),'') is not null
      and substring(trim(saksnr) from 'KON-?([A-Z0-9]+)') ~ 'K$'
    group by 1,2 order by rader desc limit 40`);

await show("B. Rader der saksnr IKKE gir kode (hele tabellen)",
  `select trim(saksnr) as saksnr, trim(tingrett) as navn, type,
          to_char(dato,'YYYY-MM-DD') as dato
     from kunngjoring.insolvens
    where nullif(trim(saksnr),'') is not null
      and substring(trim(saksnr) from 'KON-?([A-Z0-9]+)') is null
    order by dato limit 40`);

await show("C. THRD/THOD/THODK — Hordaland-kodene i tid",
  `select substring(trim(saksnr) from 'KON-?([A-Z0-9]+)') as kode, trim(tingrett) as navn,
          count(*) as rader, to_char(min(dato),'YYYY-MM-DD') as forste,
          to_char(max(dato),'YYYY-MM-DD') as siste, min(trim(saksnr)) as eks
     from kunngjoring.insolvens
    where trim(tingrett) in ('HORDALAND TINGRETT','BUSKERUD TINGRETT','OSLO TINGRETT')
    group by 1,2 order by navn, rader desc`);

await show("D. Kohorten: den ene saken uten kode",
  `with aapning as materialized (
     select orgnr, min(dato) as aapning_dato from kunngjoring.insolvens
      where type = 'Konkurs - åpning' group by orgnr),
   kohort as materialized (
     select orgnr, aapning_dato from aapning
      where aapning_dato between date '2023-09-01' and date '2024-12-31')
   select trim(i.saksnr) as saksnr, trim(i.tingrett) as navn,
          to_char(i.dato,'YYYY-MM-DD') as dato, length(trim(i.saksnr)) as len
     from kohort k join kunngjoring.insolvens i
       on i.orgnr = k.orgnr and i.dato = k.aapning_dato and i.type='Konkurs - åpning'
    where substring(trim(i.saksnr) from 'KON-?([A-Z0-9]+)') is null`);

await show("E. Kohorten: full kode x navn med KUN åpningsrad (skal være 1:1)",
  `with aapning as materialized (
     select orgnr, min(dato) as aapning_dato from kunngjoring.insolvens
      where type = 'Konkurs - åpning' group by orgnr),
   kohort as materialized (
     select orgnr, aapning_dato from aapning
      where aapning_dato between date '2023-09-01' and date '2024-12-31'),
   rad as materialized (
     select k.orgnr,
            max(nullif(trim(i.tingrett),'')) as navn,
            max(substring(trim(i.saksnr) from 'KON-?([A-Z0-9]+)')) as kode
       from kohort k join kunngjoring.insolvens i
         on i.orgnr=k.orgnr and i.dato=k.aapning_dato and i.type='Konkurs - åpning'
      group by 1)
   select kode, navn, count(*) as saker from rad group by 1,2 order by count(*) desc`);

await closePool();
