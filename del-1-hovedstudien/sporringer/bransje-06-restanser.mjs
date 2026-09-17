// bransje-06: alle 88 etiketter uten Klass-treff, og hva de er.
// Test av «flerbransje-reparasjonen»: bransje-feltet kan inneholde FLERE
// næringer skilt med linjeskift; første linje er Brregs primærnæring.
// READ-ONLY.
import { q, done, RUN_DATE } from "./_lib.mjs";
import { readFileSync } from "node:fs";

const DATA = "./data";
const kart = JSON.parse(readFileSync(`${DATA}/bransjekart-v2-klass_${RUN_DATE}.json`, "utf8")).kart;

const utenTreff = kart.filter((r) => !r.metode).sort((a, b) => b.selskaper - a.selskaper);

const out = {};
out.antall_uten_treff = utenTreff.length;
out.selskaper_uten_treff = utenTreff.reduce((s, r) => s + r.selskaper, 0);
out.alle_uten_treff = utenTreff.map((r) => ({
  etikett: r.etikett, selskaper: r.selskaper, forste: r.forste_dato, siste: r.siste_dato,
  har_linjeskift: /\n/.test(r.etikett),
}));
out.med_linjeskift = utenTreff.filter((r) => /\n/.test(r.etikett)).length;
out.selskaper_med_linjeskift = utenTreff.filter((r) => /\n/.test(r.etikett)).reduce((s, r) => s + r.selskaper, 0);

// Hvor mange rader i HELE åpningssettet har linjeskift i bransje?
out.linjeskift_hele_settet = (await q(`
  select count(distinct orgnr) filter (where bransje like E'%\\n%') as selskaper_med_linjeskift,
         count(distinct orgnr) as selskaper_totalt,
         count(distinct orgnr) filter (where trim(bransje) = 'Uoppgitt') as uoppgitt,
         count(distinct orgnr) filter (where trim(bransje) = 'Enheten er slettet') as enheten_slettet
  from kunngjoring.insolvens
  where type = 'Konkurs - åpning' and nullif(trim(bransje),'') is not null
`)).rows[0];

// Førstelinje-etiketter som IKKE finnes som egen etikett i kartet
const kjente = new Set(kart.map((r) => r.etikett.normalize("NFC")));
out.forstelinje_ukjent = utenTreff
  .filter((r) => /\n/.test(r.etikett))
  .map((r) => ({ etikett: r.etikett, forstelinje: r.etikett.split("\n")[0], kjent: kjente.has(r.etikett.split("\n")[0].normalize("NFC")) }));

// Byggrelevante restanser: sjekk mot selskapsuniversets kode for etiketten
out.byggrelevante_restanser = (await q(`
  with rest as materialized (
    select trim(bransje) as etikett, count(distinct orgnr) as selskaper
    from kunngjoring.insolvens
    where type = 'Konkurs - åpning'
      and trim(bransje) in (
        'Blikkenslagerarbeid på tak',
        'Interiørarkitekt, interiørdesign og interiørkonsulentvirksom',
        'Enheten er slettet'
      )
    group by 1
  )
  select r.etikett, r.selskaper,
         (select c.industry_code_1 from company_intel.company c
          where left(c.industry_text_1,60) = r.etikett limit 1) as kode_i_selskapstabellen
  from rest r order by r.selskaper desc
`)).rows;

console.log(JSON.stringify(out, null, 2));
await done();
