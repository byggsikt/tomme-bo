// LANE 1 / kohort — SLUTTKONTROLLER (READ-ONLY).
// 1) Forklarer byggavviket i SSB-kalibreringen fra 2025K3 (L17-sommen + 41.1 -> 68.12)
// 2) Selskaper med to aapningsrader: spriker bransje/tingrett mellom dem?
// 3) Utfyllingssensus paa aapningsraden (L5-korrekt telling)
// 4) Registerfordeling: hvem kunngjor innstillingene
import { getPool, closePool } from "./db.mjs";
import { slaaOpp, erByggF, erByggUtforende } from "./kohort-bransjeklassifikator.mjs";
const pool = getPool();
const out = (l, r) => { console.log("\n=== " + l + " ==="); console.log(JSON.stringify(r, null, 1)); };
try {
  await pool.query("set statement_timeout = '900s'");

  out("1 — SN2025-etiketter som forlot NACE 41 (eiendomsutvikling), per kvartal", (await pool.query(`
    with aapning as materialized (
      select orgnr, min(dato) as d from kunngjoring.insolvens where type='Konkurs - åpning' group by orgnr
    )
    select to_char(a.d,'YYYY')||'K'||to_char(a.d,'Q') as kvartal,
           count(distinct a.orgnr) filter (where trim(i.bransje) = 'Utvikling og salg av byggeprosjekter') as sn2025_utvikling_68_12,
           count(distinct a.orgnr) filter (where trim(i.bransje) = 'Utvikling og salg av egen fast eiendom ellers') as sn2007_utvikling_41_109
    from aapning a join kunngjoring.insolvens i on i.orgnr=a.orgnr and i.dato=a.d and i.type='Konkurs - åpning'
    where a.d >= date '2023-07-01'
    group by 1 order by 1
  `)).rows);

  out("2 — selskaper med mer enn en aapningsrad", (await pool.query(`
    select count(*) as selskaper,
           count(*) filter (where n_bransje > 1) as ulik_bransje,
           count(*) filter (where n_rett > 1) as ulik_tingrett
    from (
      select orgnr, count(*) as rader,
             count(distinct nullif(trim(bransje),'')) as n_bransje,
             count(distinct nullif(trim(tingrett),'')) as n_rett
      from kunngjoring.insolvens where type='Konkurs - åpning'
      group by orgnr having count(*) > 1
    ) t
  `)).rows);

  out("3 — utfyllingssensus paa aapningsraden i kohortvinduet (L5-korrekt)", (await pool.query(`
    with aapning as materialized (
      select orgnr, min(dato) as d from kunngjoring.insolvens where type='Konkurs - åpning' group by orgnr
    ),
    k as materialized (select orgnr, d from aapning where d between date '2023-09-01' and date '2024-12-31')
    select count(distinct k.orgnr) as selskaper,
           count(distinct k.orgnr) filter (where nullif(trim(i.bransje),'')  is not null) as bransje_utfylt,
           count(distinct k.orgnr) filter (where nullif(trim(i.tingrett),'') is not null) as tingrett_utfylt,
           count(distinct k.orgnr) filter (where nullif(trim(i.saksnr),'')   is not null) as saksnr_utfylt,
           count(distinct k.orgnr) filter (where nullif(trim(i.bostyrer),'') is not null) as bostyrer_utfylt,
           count(distinct k.orgnr) filter (where i.fristdag is not null)                  as fristdag_utfylt,
           count(distinct k.orgnr) filter (where nullif(trim(i.kapital),'')  is not null) as kapital_utfylt
    from k join kunngjoring.insolvens i on i.orgnr=k.orgnr and i.dato=k.d and i.type='Konkurs - åpning'
  `)).rows);

  out("3b — bransje utfylt paa innstillings-/avslutningsrader? (skal vaere 0)", (await pool.query(`
    select type,
           count(*) as rader,
           count(nullif(trim(bransje),''))  as bransje_utfylt,
           count(nullif(trim(tingrett),'')) as tingrett_utfylt
    from kunngjoring.insolvens
    where type in ('Konkurs - innstilling av bobehandlingen','Konkurs - avslutning av bobehandlingen')
    group by 1
  `)).rows);

  out("4 — hvem kunngjor innstillingene (register)", (await pool.query(`
    select register, count(*) as rader, count(distinct orgnr) as selskaper
    from kunngjoring.v_hendelse
    where type_kanon = 'Konkurs - innstilling av bobehandlingen'
    group by 1 order by 2 desc
  `)).rows);

  // 5 — «Oppforing av bygninger»: 600 hos oss mot 599 i briefen. Er det en dubletteffekt?
  const opp = (await pool.query(`
    with aapning as materialized (
      select orgnr, min(dato) as d from kunngjoring.insolvens where type='Konkurs - åpning' group by orgnr
    ),
    k as materialized (select orgnr, d from aapning where d between date '2023-08-24' and date '2024-12-31')
    select count(distinct k.orgnr) filter (where trim(i.bransje)='Oppføring av bygninger') as global_forste_form_A,
           (select count(distinct orgnr) from kunngjoring.insolvens
             where type='Konkurs - åpning' and dato between date '2023-08-24' and date '2024-12-31'
               and trim(bransje)='Oppføring av bygninger') as vindu_form_B
    from k join kunngjoring.insolvens i on i.orgnr=k.orgnr and i.dato=k.d and i.type='Konkurs - åpning'
  `)).rows;
  out("5 — «Oppforing av bygninger» i briefens vindu: form A mot form B", opp);
} catch (e) { console.error("FEIL:", e.message, e.stack); } finally { await closePool(); }
