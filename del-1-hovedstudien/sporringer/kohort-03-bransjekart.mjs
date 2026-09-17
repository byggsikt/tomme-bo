// LANE 1 / kohort — bransje-etikett -> NACE-kart (READ-ONLY).
//
// Doed-NACE-fellen: 97 % av slettede selskaper mangler naeringskode, saa vi kan ALDRI
// lese NACE av konkursselskapet selv. Losningen er en ORDBOK: bransje-etiketten i
// kunngjoringen er naeringens navn avkortet til 60 tegn. Vi slaar den opp mot
// left(company.industry_text_1,60) i HELE selskapsuniverset (der levende selskaper
// har koden) og laeser etikett -> kode. Kartet er en ordbok, ikke et per-selskap-oppslag.
//
// Skriver: data/bransjekart-v1.json  (versjonert, med kjoredato)
import { getPool, closePool } from "./db.mjs";
import { writeFileSync } from "node:fs";
import { createHash } from "node:crypto";

const DATA = "./data";
const pool = getPool();
const out = (label, rows) => { console.log("\n=== " + label + " ==="); console.log(JSON.stringify(rows, null, 1)); };

try {
  await pool.query("set statement_timeout = '900s'");

  // 1) Ordboken: for hver 60-tegns etikett, den hyppigste NACE-koden i selskapsuniverset.
  const kart = (await pool.query(`
    with etiketter as materialized (
      select distinct nullif(trim(bransje),'') as etikett
      from kunngjoring.insolvens
      where type = 'Konkurs - åpning' and nullif(trim(bransje),'') is not null
    ),
    univers as materialized (
      select left(industry_text_1, 60) as etikett,
             industry_code_1 as kode,
             count(*) as n
      from company_intel.company
      where industry_code_1 is not null and industry_text_1 is not null
      group by 1, 2
    ),
    rangert as (
      select e.etikett, u.kode, u.n,
             row_number() over (partition by e.etikett order by u.n desc, u.kode) as rn,
             sum(u.n) over (partition by e.etikett) as n_total,
             count(*) over (partition by e.etikett) as kandidater
      from etiketter e
      left join univers u on u.etikett = e.etikett
    )
    select etikett, kode, n, n_total, kandidater
    from rangert where rn = 1
    order by etikett
  `)).rows;

  const utenKode = kart.filter(r => r.kode === null);
  console.log("etiketter totalt:", kart.length, " uten NACE-treff:", utenKode.length);
  out("etiketter UTEN NACE-treff", utenKode.map(r => r.etikett));
  out("etiketter med flere kandidatkoder (topp 15)", kart
      .filter(r => Number(r.kandidater) > 1)
      .sort((a,b) => Number(b.kandidater) - Number(a.kandidater))
      .slice(0,15)
      .map(r => ({ etikett: r.etikett, valgt: r.kode, andel: (Number(r.n)/Number(r.n_total)).toFixed(3), kandidater: r.kandidater })));

  // 2) Hvilke etiketter blir NACE 41/42/43 (bygg)?
  const bygg = kart.filter(r => r.kode && /^(41|42|43)/.test(r.kode));
  out("BYGG-etiketter (NACE 41/42/43) fra ordboken", bygg.map(r => ({ etikett: r.etikett, kode: r.kode })));

  // 3) Kontroll: for kohortselskaper som FAKTISK har NACE, er ordboken enig?
  const kontroll = (await pool.query(`
    with aapning as materialized (
      select orgnr, min(dato) as aapning_dato
      from kunngjoring.insolvens where type='Konkurs - åpning'
      group by orgnr
    ),
    kohort as materialized (
      select a.orgnr, a.aapning_dato,
             (select max(nullif(trim(i.bransje),'')) from kunngjoring.insolvens i
               where i.orgnr=a.orgnr and i.type='Konkurs - åpning') as etikett
      from aapning a
      where a.aapning_dato between date '2023-09-01' and date '2024-12-31'
    ),
    ordbok as materialized (
      select left(industry_text_1,60) as etikett, industry_code_1 as kode,
             row_number() over (partition by left(industry_text_1,60) order by count(*) desc, industry_code_1) as rn
      from company_intel.company
      where industry_code_1 is not null and industry_text_1 is not null
      group by 1,2
    )
    select
      count(*) filter (where c.industry_code_1 is not null) as har_egen_nace,
      count(*) as kohort_n,
      count(*) filter (where c.industry_code_1 is not null and o.kode is not null
                         and left(c.industry_code_1,2) = left(o.kode,2)) as enig_2siffer,
      count(*) filter (where c.industry_code_1 is not null and o.kode is not null
                         and c.industry_code_1 = o.kode) as enig_full,
      count(*) filter (where c.industry_code_1 is not null and o.kode is not null
                         and left(c.industry_code_1,2) <> left(o.kode,2)) as uenig_2siffer
    from kohort k
    left join company_intel.company c on c.orgnr = k.orgnr
    left join ordbok o on o.etikett = k.etikett and o.rn = 1
  `)).rows;
  out("kontroll: ordbok vs selskapets egen NACE (kohorten)", kontroll);

  const payload = {
    versjon: "v1",
    kjoredato: new Date().toISOString().slice(0,10),
    beskrivelse: "bransje-etikett (60 tegn, fra kunngjoring.insolvens paa aapningsraden) -> NACE via modal industry_code_1 i selskapsuniverset",
    antall_etiketter: kart.length,
    antall_uten_treff: utenKode.length,
    bygg_koder: ["41","42","43"],
    kart: kart.map(r => ({ etikett: r.etikett, kode: r.kode, n: r.kode ? Number(r.n) : null, kandidater: Number(r.kandidater || 0) })),
  };
  const json = JSON.stringify(payload, null, 1);
  writeFileSync(DATA + "/bransjekart-v1.json", json, "utf8");
  console.log("\nskrev data/bransjekart-v1.json sha256=" + createHash("sha256").update(json).digest("hex"));
} catch (e) {
  console.error("FEIL:", e.message);
} finally {
  await closePool();
}
