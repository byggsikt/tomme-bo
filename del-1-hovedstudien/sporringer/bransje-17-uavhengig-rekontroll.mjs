// bransje-17: uavhengig rekontroll av lanens hovedtall, skrevet med en ANNEN
// SQL-form enn bransje-08/09/12 (aggregering i én spørring med FILTER-uttrykk
// i stedet for radutlevering og telling i JavaScript). Skal gi identiske tall.
// READ-ONLY.
import { q, done, writeJson, clopperPearson, RUN_DATE } from "./_lib.mjs";
import { readFileSync } from "node:fs";

const DATA = "./data";
const kart = JSON.parse(readFileSync(`${DATA}/bransjekart-v3_${RUN_DATE}.json`, "utf8")).kart;

// bygg-etikettene som en literal liste -> spørringen avhenger ikke av JS-logikk
const byggEtiketter = kart.filter((r) => r.er_bygg_F === true).map((r) => r.etikett);
const uoppgittEtiketter = kart.filter((r) => r.metode === "IKKE_NAERING").map((r) => r.etikett);

const sql = `
  with apn as materialized (
    select orgnr, min(dato) as forste, max(nullif(trim(bransje),'')) as etikett
    from kunngjoring.insolvens where type = 'Konkurs - åpning' group by orgnr
  ),
  inn as materialized (
    select distinct orgnr from kunngjoring.insolvens where type = 'Konkurs - innstilling av bobehandlingen'
  ),
  avs as materialized (
    select distinct orgnr from kunngjoring.insolvens where type = 'Konkurs - avslutning av bobehandlingen'
  ),
  koh as materialized (
    select a.orgnr, a.etikett,
           (i.orgnr is not null) as innstilt,
           (v.orgnr is not null) as avsluttet,
           (a.etikett = any($1::text[])) as bygg,
           (a.etikett = any($2::text[])) as uoppgitt
    from apn a
    left join inn i on i.orgnr = a.orgnr
    left join avs v on v.orgnr = a.orgnr
    where a.forste between date '2023-09-01' and date '2024-12-31'
  )
  select 'alle' as gruppe, count(*) as n,
         count(*) filter (where innstilt) as innstilt,
         count(*) filter (where avsluttet and not innstilt) as kun_avsluttet,
         count(*) filter (where not innstilt and not avsluttet) as apent,
         count(*) filter (where innstilt and avsluttet) as begge
  from koh
  union all
  select 'bygg', count(*), count(*) filter (where innstilt),
         count(*) filter (where avsluttet and not innstilt),
         count(*) filter (where not innstilt and not avsluttet),
         count(*) filter (where innstilt and avsluttet)
  from koh where bygg
  union all
  select 'ovrige_naeringer', count(*), count(*) filter (where innstilt),
         count(*) filter (where avsluttet and not innstilt),
         count(*) filter (where not innstilt and not avsluttet),
         count(*) filter (where innstilt and avsluttet)
  from koh where not bygg and not uoppgitt
  union all
  select 'ingen_naering_oppgitt', count(*), count(*) filter (where innstilt),
         count(*) filter (where avsluttet and not innstilt),
         count(*) filter (where not innstilt and not avsluttet),
         count(*) filter (where innstilt and avsluttet)
  from koh where uoppgitt
`;
const rows = (await q(sql, [byggEtiketter, uoppgittEtiketter])).rows;

// byggfagene, moden kohort, direkte i SQL
const byggfag = (await q(`
  with apn as materialized (
    select orgnr, min(dato) as forste, max(nullif(trim(bransje),'')) as etikett
    from kunngjoring.insolvens where type = 'Konkurs - åpning' group by orgnr
  ),
  inn as materialized (
    select distinct orgnr from kunngjoring.insolvens where type = 'Konkurs - innstilling av bobehandlingen'
  )
  select a.etikett, count(*) as n, count(i.orgnr) as innstilt
  from apn a left join inn i on i.orgnr = a.orgnr
  where a.forste between date '2023-08-24' and date '2024-12-31'
    and a.etikett in ('Snekkerarbeid','Grunnarbeid','Malerarbeid','Elektrisk installasjonsarbeid',
                      'Oppføring av bygninger','Rørleggerarbeid')
  group by 1 order by 2 desc
`)).rows;

const out = {
  kjoredato: RUN_DATE,
  hovedtall: rows.map((r) => {
    const [lo, hi] = clopperPearson(Number(r.innstilt), Number(r.n));
    return { ...r, innstilt_pst: (100 * Number(r.innstilt)) / Number(r.n),
             ki95: [100 * lo, 100 * hi] };
  }),
  byggfag_moden: byggfag.map((r) => {
    const [lo, hi] = clopperPearson(Number(r.innstilt), Number(r.n));
    return { naering: r.etikett, n: Number(r.n), innstilt: Number(r.innstilt),
             pst: (100 * Number(r.innstilt)) / Number(r.n), ki95: [100 * lo, 100 * hi] };
  }),
  forventet_fra_brief: {
    kohort: 5165, innstilt: 3897, apne: 351, begge: 6,
    byggfag: { Snekkerarbeid: [138, 178], Grunnarbeid: [81, 107], Malerarbeid: [47, 63],
               "Elektrisk installasjonsarbeid": [43, 60], "Oppføring av bygninger": [414, 599],
               Rørleggerarbeid: [55, 83] },
  },
};
writeJson(`data/bransje-rekontroll_${RUN_DATE}.json`, out);
console.log(JSON.stringify(out, null, 2));
await done();
