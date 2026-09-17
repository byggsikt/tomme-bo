// bransje-14: hvor stor er L17 for byggnæringen? Hvor mange TRYKTE etiketter
// svarer til hvor mange faktiske næringer, og hva ville naiv gruppering gitt?
// READ-ONLY.
import { q, done, writeJson, RUN_DATE } from "./_lib.mjs";
import { readFileSync } from "node:fs";

const DATA = "./data";
const kartJson = JSON.parse(readFileSync(`${DATA}/bransjekart-v3_${RUN_DATE}.json`, "utf8"));

const bygg = kartJson.kart.filter((r) => r.er_bygg_F === true);
const kanon = new Set(bygg.map((r) => r.kanonisk_sn2007));
const enkeltEtiketter = bygg.filter((r) => !r.flerbransje);

// hele materialet, ikke bare bygg
const alle = kartJson.kart.filter((r) => r.kanonisk_sn2007);
const alleKanon = new Set(alle.map((r) => r.kanonisk_sn2007));

const out = {
  kjoredato: RUN_DATE,
  bygg: {
    trykte_etiketter: bygg.length,
    trykte_etiketter_uten_flerbransje: enkeltEtiketter.length,
    kanoniske_naeringer: kanon.size,
    oppblasning_naiv_gruppering: bygg.length / kanon.size,
    etiketter_kun_for_sommen: bygg.filter((r) => r.vintage === "SN2007").length,
    etiketter_kun_etter_sommen: bygg.filter((r) => r.vintage === "SN2025").length,
    etiketter_begge_sider: bygg.filter((r) => r.vintage === "begge").length,
  },
  hele_materialet: {
    trykte_etiketter: kartJson.kart.length,
    kanoniske_naeringer: alleKanon.size,
    oppblasning_naiv_gruppering: kartJson.kart.length / alleKanon.size,
  },
};

// Kontroll: er kohortvinduet 2023-09-01..2024-12-31 helt på SN2007-siden?
out.kohortvinduet_er_rent = (await q(`
  with apn as materialized (
    select orgnr, min(dato) as forste, max(nullif(trim(bransje),'')) as etikett
    from kunngjoring.insolvens where type = 'Konkurs - åpning' group by orgnr
  )
  select count(*) as kohort,
         count(*) filter (where forste >= date '2025-09-01') as apnet_etter_sommen,
         max(forste)::text as siste_apning_i_kohorten
  from apn where forste between date '2023-09-01' and date '2024-12-31'
`)).rows[0];

// Hvor mange av kohortens etiketter finnes bare i SN2007-vintagen?
const kohortEtiketter = (await q(`
  with apn as materialized (
    select orgnr, min(dato) as forste, max(nullif(trim(bransje),'')) as etikett
    from kunngjoring.insolvens where type = 'Konkurs - åpning' group by orgnr
  )
  select etikett, count(*) as selskaper from apn
  where forste between date '2023-09-01' and date '2024-12-31' group by 1
`)).rows;
const kartMap = new Map(kartJson.kart.map((r) => [r.etikett.normalize("NFC"), r]));
let sn2007only = 0, sn2007onlySelsk = 0;
for (const e of kohortEtiketter) {
  const k = kartMap.get(e.etikett.normalize("NFC"));
  if (k?.vintage === "SN2007") { sn2007only++; sn2007onlySelsk += Number(e.selskaper); }
}
out.kohortens_etiketter = {
  distinkte: kohortEtiketter.length,
  kun_sn2007_vintage: sn2007only,
  selskaper_med_sn2007_kun_etikett: sn2007onlySelsk,
  andel_pst: (100 * sn2007onlySelsk) / kohortEtiketter.reduce((s, r) => s + Number(r.selskaper), 0),
};

writeJson(`data/bransje-L17-omfang_${RUN_DATE}.json`, out);
console.log(JSON.stringify(out, null, 2));
await done();
