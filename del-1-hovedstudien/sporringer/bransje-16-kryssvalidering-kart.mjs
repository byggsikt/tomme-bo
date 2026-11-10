// bransje-16: kryssvalidering av kartet.
// Der BÅDE Klass-metoden (v3) og oppslag mot left(company.industry_text_1, 60)
// gir en kode: hvor ofte er de enige? Uenighet er enten navnedrift eller en
// vintagefeil, og hver enkelt skal kunne forklares.
// READ-ONLY.
import { q, done, writeCsv, writeJson, RUN_DATE } from "./_lib.mjs";
import { readFileSync } from "node:fs";

const DATA = "./data";
const kartJson = JSON.parse(readFileSync(`${DATA}/bransjekart-v3_${RUN_DATE}.json`, "utf8"));

// modal kode i selskapsuniverset per 60-tegns tekst
const modal = new Map();
for (const r of (await q(`
  select left(industry_text_1, 60) as t, industry_code_1 as kode, count(*) as n
  from company_intel.company
  where nullif(trim(industry_text_1),'') is not null
    and nullif(trim(industry_code_1),'') is not null
  group by 1,2
`)).rows) {
  const k = (r.t ?? "").normalize("NFC").replace(/\s+/g, " ").trim();
  const prev = modal.get(k);
  if (!prev || Number(r.n) > prev.n) modal.set(k, { kode: r.kode, n: Number(r.n) });
}

const rader = [];
let begge = 0, enige = 0, uenige = 0, kunKlass = 0, kunSelskapstekst = 0, ingen = 0;
for (const r of kartJson.kart) {
  const k = (r.etikett ?? "").normalize("NFC").replace(/\s+/g, " ").trim();
  const m = modal.get(k) ?? null;
  const klassKode = r.kode ?? null;              // koden i den standarden treffet kom fra
  if (klassKode && m) {
    begge++;
    if (klassKode === m.kode) enige++;
    else { uenige++; rader.push({ etikett: r.etikett, selskaper: r.selskaper, klass: klassKode, klass_std: r.standard, selskapstekst: m.kode, vintage: r.vintage, metode: r.metode }); }
  } else if (klassKode) kunKlass++;
  else if (m) kunSelskapstekst++;
  else ingen++;
}

const out = {
  kjoredato: RUN_DATE,
  etiketter: kartJson.kart.length,
  begge_metoder_gir_kode: begge,
  enige: enige,
  uenige: uenige,
  enighet_pst: (100 * enige) / begge,
  kun_klass: kunKlass,
  kun_selskapstekst: kunSelskapstekst,
  ingen_av_delene: ingen,
  uenigheter: rader.sort((a, b) => b.selskaper - a.selskaper),
};

// Hva ville et rent selskapstekst-kart ha gitt for bygg i hele åpningsserien?
let byggKlass = 0, byggModal = 0;
for (const r of kartJson.kart) {
  const k = (r.etikett ?? "").normalize("NFC").replace(/\s+/g, " ").trim();
  const m = modal.get(k) ?? null;
  if (r.er_bygg_F) byggKlass += r.selskaper;
  if (/^4[123]/.test(m?.kode || "")) byggModal += r.selskaper;
}
out.bygg_hele_serien = { klass_v3: byggKlass, modal_selskapstekst: byggModal, tapt: byggKlass - byggModal,
  tapt_pst: (100 * (byggKlass - byggModal)) / byggKlass };

writeCsv(`data/bransjekart-kryssvalidering_${RUN_DATE}.csv`,
  ["etikett", "selskaper", "kode_klass", "standard_klass", "kode_selskapstekst", "vintage", "metode"],
  rader.map((r) => [r.etikett.replace(/\n/g, " \\n "), r.selskaper, r.klass, r.klass_std, r.selskapstekst, r.vintage, r.metode]));

writeJson(`data/bransjekart-kryssvalidering_${RUN_DATE}.json`, out);
console.log(JSON.stringify(out, null, 2));
await done();
