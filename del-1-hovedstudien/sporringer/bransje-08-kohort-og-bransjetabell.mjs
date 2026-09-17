// bransje-08: kohorten, utfallet og bransjetabellen.
//
// Kohort: distinkte orgnr med type = 'Konkurs - åpning'. To definisjoner regnes ut:
//   A  global første åpning per orgnr, deretter filtrert til vinduet (primær)
//   B  minste åpningsdato INNENFOR vinduet (den formen de verifiserte tallene brukte)
// Utfall: LEFT JOIN mot distinkte orgnr-sett for innstilling og avslutning.
// Bransje: max(nullif(trim(bransje),'')) på åpningsraden -> bransjekart v3.
// Alt telles som count(distinct orgnr) (L8/L14). MATERIALIZED CTE-form (ytelse).
// READ-ONLY.
import { q, done, writeCsv, writeJson, clopperPearson, RUN_DATE } from "./_lib.mjs";
import { readFileSync } from "node:fs";

const DATA = "./data";
const kartRader = JSON.parse(readFileSync(`${DATA}/bransjekart-v3_${RUN_DATE}.json`, "utf8")).kart;
const kart = new Map(kartRader.map((r) => [r.etikett.normalize("NFC"), r]));

const VINDU = { start: "2023-09-01", slutt: "2024-12-31" };   // hovedvindu
const MODEN = { start: "2023-08-24", slutt: "2024-12-31" };   // «moden kohort» i briefen

async function kohort(vindu, form) {
  const filter = form === "A"
    ? `where a.forste_apning between date '${vindu.start}' and date '${vindu.slutt}'`
    : `where a.forste_apning_i_vindu is not null`;
  const apning = form === "A"
    ? `select orgnr, min(dato) as forste_apning,
              max(nullif(trim(bransje),'')) as bransje_etikett,
              count(*) as apningsrader,
              count(distinct nullif(trim(bransje),'')) as distinkte_etiketter
       from kunngjoring.insolvens where type = 'Konkurs - åpning' group by orgnr`
    : `select orgnr, min(dato) filter (where dato between date '${vindu.start}' and date '${vindu.slutt}') as forste_apning_i_vindu,
              min(dato) as forste_apning,
              max(nullif(trim(bransje),'')) as bransje_etikett,
              count(*) as apningsrader,
              count(distinct nullif(trim(bransje),'')) as distinkte_etiketter
       from kunngjoring.insolvens where type = 'Konkurs - åpning' group by orgnr`;

  const sql = `
    with apn as materialized ( ${apning} ),
    koh as materialized ( select * from apn a ${filter} ),
    inn as materialized (
      select orgnr, min(dato) as dato from kunngjoring.insolvens
      where type ilike 'Konkurs - innstilling%' group by orgnr
    ),
    avs as materialized (
      select orgnr, min(dato) as dato from kunngjoring.insolvens
      where type ilike 'Konkurs - avslutning%' group by orgnr
    )
    select k.orgnr,
           ${form === "A" ? "k.forste_apning" : "k.forste_apning_i_vindu"}::text as apningsdato,
           k.bransje_etikett, k.apningsrader, k.distinkte_etiketter,
           i.dato::text as innstilt_dato, v.dato::text as avsluttet_dato
    from koh k
    left join inn i on i.orgnr = k.orgnr
    left join avs v on v.orgnr = k.orgnr
  `;
  return (await q(sql)).rows;
}

const t0 = Date.now();
const A = await kohort(VINDU, "A");
const B = await kohort(VINDU, "B");
const M = await kohort(MODEN, "B");   // moden kohort, in-window-min (som briefen)
const kjoretid_s = ((Date.now() - t0) / 1000).toFixed(1);

function utfall(rader) {
  let innstilt = 0, avsluttet = 0, apen = 0, begge = 0;
  for (const r of rader) {
    const i = !!r.innstilt_dato, a = !!r.avsluttet_dato;
    if (i && a) begge++;
    if (i) innstilt++;
    else if (a) avsluttet++;
    else apen++;
  }
  return { n: rader.length, innstilt, avsluttet, apen, begge,
           innstilt_pst: (100 * innstilt) / rader.length };
}

function merk(rader) {
  for (const r of rader) {
    const k = r.bransje_etikett ? kart.get(r.bransje_etikett.normalize("NFC")) : null;
    r.kart = k ?? null;
    r.kanonisk = k?.kanonisk_sn2007 ?? null;
    r.kanonisk_navn = k?.kanonisk_navn ?? null;
    r.er_bygg_F = k?.er_bygg_F === true;
    r.er_bygg_kjerne = k?.er_bygg_kjerne === true;
    r.uoppgitt = k?.metode === "IKKE_NAERING";
    r.uten_kode = !!k && !k.kanonisk_sn2007 && k.metode !== "IKKE_NAERING";
    r.mangler_etikett = !r.bransje_etikett;
  }
  return rader;
}
merk(A); merk(B); merk(M);

const out = { kjoredato: RUN_DATE, kjoretid_sekunder: Number(kjoretid_s) };
out.kohort_A_global_forste = { vindu: VINDU, ...utfall(A) };
out.kohort_B_min_i_vindu = { vindu: VINDU, ...utfall(B) };
out.kohort_M_moden = { vindu: MODEN, ...utfall(M) };
out.differanse_A_vs_B = B.length - A.length;

// --- bygg vs øvrige, begge byggdefinisjoner, på kohort A og B ---
function del(rader, pred) { return utfall(rader.filter(pred)); }
for (const [navn, rader] of [["A", A], ["B", B], ["M", M]]) {
  out[`bygg_${navn}`] = {
    bygg_F_41_42_43: del(rader, (r) => r.er_bygg_F),
    bygg_kjerne_41_2_42_43: del(rader, (r) => r.er_bygg_kjerne),
    ovrige_F: del(rader, (r) => !r.er_bygg_F),
    uoppgitt: del(rader, (r) => r.uoppgitt),
    uten_kode: del(rader, (r) => r.uten_kode),
    mangler_etikett: del(rader, (r) => r.mangler_etikett),
  };
}

// --- etikettstabilitet: samme selskap, flere åpningsrader ---
out.etikettstabilitet = (await q(`
  with a as materialized (
    select orgnr, count(*) as rader,
           count(nullif(trim(bransje),'')) as rader_med_bransje,
           count(distinct nullif(trim(bransje),'')) as distinkte_etiketter
    from kunngjoring.insolvens where type = 'Konkurs - åpning' group by orgnr
  )
  select count(*) as selskaper,
         count(*) filter (where rader > 1) as med_flere_rader,
         count(*) filter (where rader_med_bransje > 1) as med_flere_bransjerader,
         count(*) filter (where distinkte_etiketter > 1) as med_ulik_etikett,
         max(rader) as maks_rader, max(distinkte_etiketter) as maks_distinkte
  from a
`)).rows[0];

out.etikettstabilitet_eksempler = (await q(`
  with a as materialized (
    select orgnr from kunngjoring.insolvens
    where type = 'Konkurs - åpning'
    group by orgnr having count(distinct nullif(trim(bransje),'')) > 1
  )
  select i.dato::text as dato, trim(i.bransje) as etikett
  from kunngjoring.insolvens i join a on a.orgnr = i.orgnr
  where i.type = 'Konkurs - åpning' and nullif(trim(i.bransje),'') is not null
  order by i.orgnr, i.dato limit 40
`)).rows;

// --- død-NACE-fellen, målt på kohorten ---
const orgnrA = A.map((r) => r.orgnr);
out.dod_nace = (await q(`
  with koh as materialized (
    select unnest($1::text[]) as orgnr
  )
  select count(*) as kohort,
         count(c.orgnr) as har_rad_i_selskapstabellen,
         count(*) filter (where c.is_deleted) as slettet_i_registeret,
         count(nullif(trim(c.industry_code_1),'')) as har_naeringskode,
         count(nullif(trim(c.industry_code_1),'')) filter (where c.is_deleted) as slettet_med_naeringskode,
         count(*) filter (where c.is_deleted) - count(nullif(trim(c.industry_code_1),'')) filter (where c.is_deleted) as slettet_uten_naeringskode
  from koh k left join company_intel.company c on c.orgnr = k.orgnr
`, [orgnrA])).rows[0];

// samme test på HELE konkursåpningsuniverset (13 644)
out.dod_nace_alle = (await q(`
  with koh as materialized (
    select distinct orgnr from kunngjoring.insolvens where type = 'Konkurs - åpning'
  )
  select count(*) as selskaper,
         count(c.orgnr) as har_rad_i_selskapstabellen,
         count(*) filter (where c.is_deleted) as slettet_i_registeret,
         count(nullif(trim(c.industry_code_1),'')) as har_naeringskode,
         count(nullif(trim(c.industry_code_1),'')) filter (where c.is_deleted) as slettet_med_naeringskode
  from koh k left join company_intel.company c on c.orgnr = k.orgnr
`)).rows[0];

// Frossent uttrekk fra denne lanen er AGGREGERT — aldri én rad per foretak.
// Personvernregelen: ingen enkeltselskaper i noen fil, heller ikke som organisasjonsnummer.
// Radnivåfrysen av kohorten eies av kohort-lanen; denne lanen leverer bare aggregater.
// Aggregeringsnivå: næring x åpningskvartal. Celler med færre enn 10 bo slås
// sammen til én undertrykt rad, slik at ingen liten gruppe kan spores tilbake.
const MIN_CELLE = 10;
const kvartal = (d) => `${d.slice(0, 4)}K${Math.floor((Number(d.slice(5, 7)) - 1) / 3) + 1}`;
const agg = new Map();
for (const r of A) {
  const key = [r.kanonisk ?? "(ingen kode)", r.kanonisk_navn ?? "", kvartal(r.apningsdato),
               r.er_bygg_F, r.er_bygg_kjerne].join("|");
  const b = agg.get(key) ?? { n: 0, innstilt: 0, avsluttet: 0, apent: 0 };
  b.n++;
  if (r.innstilt_dato) b.innstilt++; else if (r.avsluttet_dato) b.avsluttet++; else b.apent++;
  agg.set(key, b);
}
const publ = [...agg].filter(([, b]) => b.n >= MIN_CELLE);
const und = [...agg].filter(([, b]) => b.n < MIN_CELLE);
const uS = und.reduce((s, [, b]) => ({ n: s.n + b.n, innstilt: s.innstilt + b.innstilt,
  avsluttet: s.avsluttet + b.avsluttet, apent: s.apent + b.apent }), { n: 0, innstilt: 0, avsluttet: 0, apent: 0 });
const frys = writeCsv(`data/bransje-kohortaggregat-A_${RUN_DATE}.csv`,
  ["kanonisk_sn2007", "kanonisk_navn", "apningskvartal", "er_bygg_F", "er_bygg_kjerne",
   "antall_bo", "innstilt", "avsluttet", "fortsatt_apent"],
  [...publ.sort((a, b) => b[1].n - a[1].n).map(([k, b]) => [...k.split("|"), b.n, b.innstilt, b.avsluttet, b.apent]),
   ["(undertrykt)", `Celler med færre enn ${MIN_CELLE} bo, slått sammen (${und.length} celler)`,
    "alle", "", "", uS.n, uS.innstilt, uS.avsluttet, uS.apent]]);
out.frossent_aggregat = { ...frys, publiserte_celler: publ.length, undertrykte_celler: und.length, undertrykte_bo: uS.n };

writeJson(`data/bransje-kohort-rapport_${RUN_DATE}.json`, out);
console.log(JSON.stringify(out, null, 2));
await done();
