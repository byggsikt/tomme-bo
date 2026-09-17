// bransje-05: bygg det VERSJONERTE kartet bransje-etikett -> NACE, med begge
// klassifikasjonsvintager (SN2007 og SN2025) og sømmen 2025-09-01 (L17).
//
// Metode (i prioritert rekkefølge per etikett):
//   T1  eksakt treff mot SSB Klass-navn (nivå 5) avkortet til 60 tegn — SN2007
//   T2  samme mot SN2025
//   T3  eksakt treff mot Klass-navn på nivå 4 (grupperingsnivå), begge vintager
//   T4  eksakt treff mot left(company_intel.company.industry_text_1, 60)  [kryssjekk]
// Vintage avgjøres av observert datospenn rundt sømmen 2025-09-01.
// Kanonisk analyseenhet = SN2007 femsifret kode; SN2025-etiketter brytes tilbake
// via SSBs offisielle korrespondansetabell 2919.
//
// READ-ONLY mot databasen.
import { q, done, writeCsv, writeJson, RUN_DATE } from "./_lib.mjs";
import { readFileSync } from "node:fs";

const DATA = "./data";
const SEAM = "2025-09-01";

// ---------- last Klass ----------
function lesCsv(fil) {
  const txt = readFileSync(`${DATA}/${fil}`, "utf8").trim().split(/\r?\n/);
  const head = txt[0].split(",");
  return txt.slice(1).map((line) => {
    const cells = [];
    let cur = "", inQ = false;
    for (let i = 0; i < line.length; i++) {
      const ch = line[i];
      if (inQ) {
        if (ch === '"' && line[i + 1] === '"') { cur += '"'; i++; }
        else if (ch === '"') inQ = false;
        else cur += ch;
      } else if (ch === '"') inQ = true;
      else if (ch === ",") { cells.push(cur); cur = ""; }
      else cur += ch;
    }
    cells.push(cur);
    return Object.fromEntries(head.map((h, i) => [h, cells[i]]));
  });
}

const norm = (s) => (s ?? "").normalize("NFC").replace(/\s+/g, " ").trim();
const key60 = (s) => norm(norm(s).slice(0, 60));

const sn2007 = lesCsv(`klass-SN2007-koder_${RUN_DATE}.csv`);
const sn2025 = lesCsv(`klass-SN2025-koder_${RUN_DATE}.csv`);
const korr = lesCsv(`klass-korrespondanse-SN2025-SN2007_${RUN_DATE}.csv`);

function byggIndeks(koder, niva) {
  const m = new Map();
  for (const k of koder) {
    if (String(k.niva) !== String(niva)) continue;
    const kk = key60(k.navn);
    if (!m.has(kk)) m.set(kk, []);
    m.get(kk).push({ kode: k.kode, navn: k.navn, niva: k.niva });
  }
  return m;
}
const idx = {
  sn2007_5: byggIndeks(sn2007, 5), sn2007_4: byggIndeks(sn2007, 4),
  sn2025_5: byggIndeks(sn2025, 5), sn2025_4: byggIndeks(sn2025, 4),
};

// SN2025 -> SN2007 (kan være én-til-mange)
const korrMap = new Map();
for (const r of korr) {
  if (!korrMap.has(r.sn2025_kode)) korrMap.set(r.sn2025_kode, []);
  korrMap.get(r.sn2025_kode).push({ kode: r.sn2007_kode, navn: r.sn2007_navn });
}

// ---------- etiketter fra databasen ----------
const etiketter = (await q(`
  select trim(bransje) as etikett,
         count(distinct orgnr) as selskaper,
         min(dato)::text as forste_dato,
         max(dato)::text as siste_dato,
         count(distinct orgnr) filter (where dato <  date '${SEAM}') as selsk_for_som,
         count(distinct orgnr) filter (where dato >= date '${SEAM}') as selsk_etter_som
  from kunngjoring.insolvens
  where type = 'Konkurs - åpning' and nullif(trim(bransje),'') is not null
  group by 1
  order by 2 desc
`)).rows;

// kryssjekk mot selskapsuniverset (SN2025-vintage i company-tabellen)
const selskapstekst = new Map();
for (const r of (await q(`
  select left(industry_text_1, 60) as t, industry_code_1 as kode, count(*) as n
  from company_intel.company
  where nullif(trim(industry_text_1),'') is not null
    and nullif(trim(industry_code_1),'') is not null
  group by 1,2
`)).rows) {
  const k = key60(r.t);
  const prev = selskapstekst.get(k);
  if (!prev || Number(r.n) > prev.n) selskapstekst.set(k, { kode: r.kode, n: Number(r.n) });
}

// ---------- match ----------
const kart = [];
const stats = { T1_sn2007_niva5: 0, T2_sn2025_niva5: 0, T3_niva4: 0, T4_selskapstekst: 0, ingen: 0 };

for (const e of etiketter) {
  const k = key60(e.etikett);
  const forSom = Number(e.selsk_for_som) > 0;
  const etterSom = Number(e.selsk_etter_som) > 0;
  const vintage = forSom && etterSom ? "begge" : etterSom ? "SN2025" : "SN2007";

  const t2007 = idx.sn2007_5.get(k) || [];
  const t2025 = idx.sn2025_5.get(k) || [];
  const t2007_4 = idx.sn2007_4.get(k) || [];
  const t2025_4 = idx.sn2025_4.get(k) || [];

  let metode = null, sn07 = null, sn25 = null, niva = null;

  if (t2007.length) { sn07 = t2007[0]; metode = "T1"; niva = 5; }
  if (t2025.length) { sn25 = t2025[0]; if (!metode) { metode = "T2"; niva = 5; } }
  if (!metode && t2007_4.length) { sn07 = t2007_4[0]; metode = "T3"; niva = 4; }
  if (!metode && t2025_4.length) { sn25 = t2025_4[0]; metode = "T3"; niva = 4; }

  const kryss = selskapstekst.get(k) || null;
  if (!metode && kryss) { metode = "T4"; sn25 = { kode: kryss.kode, navn: e.etikett, niva: "5?" }; }

  // kanonisk SN2007-kode: direkte hvis vi har den, ellers via korrespondansen
  let kanonKode = sn07?.kode ?? null;
  let kanonNavn = sn07?.navn ?? null;
  let kanonKilde = sn07 ? "direkte" : null;
  let korrGrener = [];
  if (!kanonKode && sn25?.kode) {
    korrGrener = korrMap.get(sn25.kode) || [];
    if (korrGrener.length === 1) {
      kanonKode = korrGrener[0].kode; kanonNavn = korrGrener[0].navn; kanonKilde = "korrespondanse-1til1";
    } else if (korrGrener.length > 1) {
      kanonKode = korrGrener.map((g) => g.kode).sort().join("|");
      kanonNavn = korrGrener.map((g) => g.navn).join(" | ");
      kanonKilde = "korrespondanse-1tilmange";
    }
  }

  if (metode === "T1") stats.T1_sn2007_niva5++;
  else if (metode === "T2") stats.T2_sn2025_niva5++;
  else if (metode === "T3") stats.T3_niva4++;
  else if (metode === "T4") stats.T4_selskapstekst++;
  else stats.ingen++;

  const bygg = (s) => /^4[123]/.test(s || "");
  kart.push({
    etikett: e.etikett,
    selskaper: Number(e.selskaper),
    forste_dato: e.forste_dato,
    siste_dato: e.siste_dato,
    selsk_for_som: Number(e.selsk_for_som),
    selsk_etter_som: Number(e.selsk_etter_som),
    vintage,
    metode,
    sn2007_kode: sn07?.kode ?? null,
    sn2007_navn: sn07?.navn ?? null,
    sn2025_kode: sn25?.kode ?? null,
    sn2025_navn: sn25?.navn ?? null,
    kanonisk_sn2007: kanonKode,
    kanonisk_navn: kanonNavn,
    kanonisk_kilde: kanonKilde,
    er_bygg_sn2007: kanonKode ? kanonKode.split("|").some(bygg) : null,
    er_bygg_sn2025: sn25?.kode ? bygg(sn25.kode) : null,
    selskapstekst_kode: kryss?.kode ?? null,
    niva: niva,
  });
}

// ---------- rapport ----------
const utenTreff = kart.filter((r) => !r.metode).sort((a, b) => b.selskaper - a.selskaper);
const utenKanon = kart.filter((r) => r.metode && !r.kanonisk_sn2007).sort((a, b) => b.selskaper - a.selskaper);
const sumSelsk = kart.reduce((s, r) => s + r.selskaper, 0);
const sumTruffet = kart.filter((r) => r.kanonisk_sn2007).reduce((s, r) => s + r.selskaper, 0);

const rapport = {
  kjoredato: RUN_DATE,
  antall_etiketter: kart.length,
  selskaper_dekket_av_etiketter: sumSelsk,
  selskaper_med_kanonisk_sn2007: sumTruffet,
  andel_selskaper_kanonisert: (100 * sumTruffet) / sumSelsk,
  metodefordeling: stats,
  etiketter_uten_treff: utenTreff.length,
  etiketter_uten_kanonisk: utenKanon.length,
  vintagefordeling: {
    kun_sn2007: kart.filter((r) => r.vintage === "SN2007").length,
    kun_sn2025: kart.filter((r) => r.vintage === "SN2025").length,
    begge: kart.filter((r) => r.vintage === "begge").length,
  },
  topp_uten_treff: utenTreff.slice(0, 25).map((r) => ({ etikett: r.etikett, selskaper: r.selskaper, forste: r.forste_dato, siste: r.siste_dato })),
  topp_uten_kanonisk: utenKanon.slice(0, 15).map((r) => ({ etikett: r.etikett, selskaper: r.selskaper, metode: r.metode, sn2025: r.sn2025_kode })),
  bygg_etiketter_sn2007: kart.filter((r) => r.er_bygg_sn2007).length,
  bygg_selskaper_sn2007: kart.filter((r) => r.er_bygg_sn2007).reduce((s, r) => s + r.selskaper, 0),
};

const csv = writeCsv(
  `data/bransjekart-v2-klass_${RUN_DATE}.csv`,
  ["etikett", "selskaper", "forste_dato", "siste_dato", "selsk_for_som", "selsk_etter_som", "vintage",
   "metode", "sn2007_kode", "sn2007_navn", "sn2025_kode", "sn2025_navn",
   "kanonisk_sn2007", "kanonisk_navn", "kanonisk_kilde", "er_bygg_sn2007", "er_bygg_sn2025", "selskapstekst_kode"],
  kart.map((r) => [r.etikett, r.selskaper, r.forste_dato, r.siste_dato, r.selsk_for_som, r.selsk_etter_som, r.vintage,
    r.metode ?? "", r.sn2007_kode ?? "", r.sn2007_navn ?? "", r.sn2025_kode ?? "", r.sn2025_navn ?? "",
    r.kanonisk_sn2007 ?? "", r.kanonisk_navn ?? "", r.kanonisk_kilde ?? "",
    r.er_bygg_sn2007 === null ? "" : r.er_bygg_sn2007, r.er_bygg_sn2025 === null ? "" : r.er_bygg_sn2025,
    r.selskapstekst_kode ?? ""])
);

const js = writeJson(`data/bransjekart-v2-klass_${RUN_DATE}.json`, {
  versjon: "v2",
  kjoredato: RUN_DATE,
  beskrivelse:
    "Kart fra bransje-etiketten på konkursåpningsraden (avkortet ved 60 tegn i kilden) til NACE. " +
    "Kodene er hentet fra SSBs Klass-API: klassifikasjon 6, versjon 30 (SN2007) og 3218 (SN2025); " +
    "SN2025->SN2007 via SSBs korrespondansetabell 2919. Sømmen mellom vintagene ligger 2025-09-01.",
  kilder: {
    sn2007: "https://data.ssb.no/api/klass/v1/versions/30",
    sn2025: "https://data.ssb.no/api/klass/v1/versions/3218",
    korrespondanse: "https://data.ssb.no/api/klass/v1/correspondencetables/2919",
  },
  som_dato: SEAM,
  rapport,
  kart,
});

console.log(JSON.stringify({ ...rapport, csv, js }, null, 2));
await done();
