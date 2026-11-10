// bransje-01: sensus over bransje-etiketter på konkursåpningsrader + søm-deteksjon (L17).
// READ-ONLY. Kun SELECT.
//
// Spørsmål:
//  a) Hvor mange distinkte etiketter finnes, og hva er datospennet per etikett?
//  b) Hvilke etiketter slutter / starter rundt sømmen 2025-08-31 (SN2007 -> SN2025)?
//  c) Er innstillings-/avslutningsserien i kunngjoring.insolvens den samme som i v_hendelse?
import { q, done, writeCsv, RUN_DATE } from "./_lib.mjs";

const out = {};

// (c) seriestart-kontroll mot v_hendelse — brief oppgir 2023-08-24 / 2023-06-01
out.seriestart = (await q(`
  select 'insolvens' as kilde, type as etikett,
         min(dato)::text as forste, max(dato)::text as siste,
         count(distinct orgnr) as selskaper
  from kunngjoring.insolvens
  where type in ('Konkurs - innstilling av bobehandlingen',
                 'Konkurs - avslutning av bobehandlingen',
                 'Konkurs - åpning')
  group by type
  union all
  select 'v_hendelse', type_kanon,
         min(dato)::text, max(dato)::text, count(distinct orgnr)
  from kunngjoring.v_hendelse
  where type_kanon in ('Konkurs - innstilling av bobehandlingen',
                       'Konkurs - avslutning av bobehandlingen',
                       'Konkurs - åpning')
  group by type_kanon
  order by 1, 2
`)).rows;

// (a)+(b) etikettsensus med datospenn
const sensus = (await q(`
  select trim(bransje) as etikett,
         count(*) as rader,
         count(distinct orgnr) as selskaper,
         min(dato)::text as forste_dato,
         max(dato)::text as siste_dato,
         count(*) filter (where dato < date '2025-09-01') as rader_for_som,
         count(*) filter (where dato >= date '2025-09-01') as rader_etter_som,
         max(length(trim(bransje))) as etikettlengde
  from kunngjoring.insolvens
  where type = 'Konkurs - åpning'
    and nullif(trim(bransje),'') is not null
  group by 1
  order by selskaper desc
`)).rows;

out.antall_etiketter = sensus.length;
out.etiketter_kun_for_som = sensus.filter((r) => Number(r.rader_etter_som) === 0).length;
out.etiketter_kun_etter_som = sensus.filter((r) => Number(r.rader_for_som) === 0).length;
out.etiketter_begge_sider = sensus.filter(
  (r) => Number(r.rader_for_som) > 0 && Number(r.rader_etter_som) > 0
).length;
out.etiketter_60_tegn = sensus.filter((r) => Number(r.etikettlengde) === 60).length;

// De 30 største etikettene, til øyekontroll
out.topp30 = sensus.slice(0, 30).map((r) => ({
  etikett: r.etikett,
  selskaper: Number(r.selskaper),
  forste: r.forste_dato,
  siste: r.siste_dato,
  for_som: Number(r.rader_for_som),
  etter_som: Number(r.rader_etter_som),
}));

// Etiketter som DØR ved sømmen (siste dato i aug 2025) — SN2007-vintage
out.dor_ved_som = sensus
  .filter((r) => r.siste_dato >= "2025-06-01" && r.siste_dato < "2025-09-01" && Number(r.selskaper) >= 5)
  .map((r) => ({ etikett: r.etikett, selskaper: Number(r.selskaper), siste: r.siste_dato }))
  .sort((a, b) => b.selskaper - a.selskaper);

// Etiketter som FØDES ved sømmen (første dato fra sep 2025) — SN2025-vintage
out.fodes_ved_som = sensus
  .filter((r) => r.forste_dato >= "2025-08-01" && Number(r.selskaper) >= 2)
  .map((r) => ({ etikett: r.etikett, selskaper: Number(r.selskaper), forste: r.forste_dato }))
  .sort((a, b) => b.selskaper - a.selskaper);

const csv = writeCsv(
  `data/bransje-etikett-sensus_${RUN_DATE}.csv`,
  ["etikett", "rader", "selskaper", "forste_dato", "siste_dato", "rader_for_2025_09_01", "rader_fra_2025_09_01", "etikettlengde"],
  sensus.map((r) => [r.etikett, r.rader, r.selskaper, r.forste_dato, r.siste_dato, r.rader_for_som, r.rader_etter_som, r.etikettlengde])
);
out.csv = csv;

console.log(JSON.stringify(out, null, 2));
await done();
