// bransje-07: ENDELIG versjonert kart  bransje-etikett -> NACE  (bransjekart v3).
//
// Kilde for kodene: SSB Klass-API, klassifikasjon 6 «Standard for næringsgruppering (SN)»,
//   versjon 30  = SN2007  (gyldig 2009-01-01 -> 2025-01-01)
//   versjon 3218 = SN2025 (gyldig fra 2025-01-01)
//   korrespondansetabell 2919 = SN2025 -> SN2007
// Etikettene kommer fra åpningsraden i konkurskunngjøringen og er avkortet ved 60 tegn.
// Sømmen mellom vintagene i vårt materiale ligger 2025-09-01 (L17).
//
// Matchtrinn, i prioritert rekkefølge:
//   T0  flerbransje-reparasjon: feltet kan inneholde flere næringer skilt med
//       linjeskift; første linje er primærnæringen. 83 selskaper av 13 644.
//   T1  eksakt treff mot SN2007-navn (nivå 5), avkortet til 60 tegn
//   T2  eksakt treff mot SN2025-navn (nivå 5), avkortet til 60 tegn
//   T3  eksakt treff mot nivå 4 i en av standardene
//   T5  toveis normalisert prefiksmatch (entydig): etiketten er prefiks av
//       standardnavnet, eller standardnavnet er prefiks av etiketten.
//       Fanger navnedriften mellom Brønnøysunds og SSBs skrivemåte.
//   T6  manuell tilordning, med skriftlig begrunnelse per rad
//   --  IKKE_NAERING: verdier som ikke er en næring i det hele tatt
//       («Uoppgitt», «Enheten er slettet») rapporteres som egen kategori,
//       aldri omfordelt.
//
// READ-ONLY mot databasen.
import { q, done, writeCsv, writeJson, RUN_DATE } from "./_lib.mjs";
import { readFileSync } from "node:fs";

const DATA = "./data";
const SEAM = "2025-09-01";
const MIN_PREFIX = 12;

function lesCsv(fil) {
  const txt = readFileSync(`${DATA}/${fil}`, "utf8").trim().split(/\r?\n/);
  const head = txt[0].split(",");
  return txt.slice(1).map((line) => {
    const cells = []; let cur = "", inQ = false;
    for (let i = 0; i < line.length; i++) {
      const ch = line[i];
      if (inQ) { if (ch === '"' && line[i + 1] === '"') { cur += '"'; i++; } else if (ch === '"') inQ = false; else cur += ch; }
      else if (ch === '"') inQ = true;
      else if (ch === ",") { cells.push(cur); cur = ""; }
      else cur += ch;
    }
    cells.push(cur);
    return Object.fromEntries(head.map((h, i) => [h, cells[i]]));
  });
}

const nfc = (s) => (s ?? "").normalize("NFC").replace(/\s+/g, " ").trim();
const key60 = (s) => nfc(nfc(s).slice(0, 60));
const skarp = (s) => nfc(s).toLowerCase().replace(/[^\p{L}\p{N}]/gu, "");

const sn = {
  SN2007: lesCsv(`klass-SN2007-koder_${RUN_DATE}.csv`),
  SN2025: lesCsv(`klass-SN2025-koder_${RUN_DATE}.csv`),
};
const korr = lesCsv(`klass-korrespondanse-SN2025-SN2007_${RUN_DATE}.csv`);
const korrMap = new Map();
for (const r of korr) {
  if (!korrMap.has(r.sn2025_kode)) korrMap.set(r.sn2025_kode, []);
  korrMap.get(r.sn2025_kode).push({ kode: r.sn2007_kode, navn: r.sn2007_navn });
}

function eksaktIndeks(rader, niva) {
  const m = new Map();
  for (const k of rader) {
    if (String(k.niva) !== String(niva)) continue;
    const kk = key60(k.navn);
    if (!m.has(kk)) m.set(kk, { kode: k.kode, navn: k.navn, niva: Number(k.niva) });
  }
  return m;
}
const idx = {
  SN2007: { 5: eksaktIndeks(sn.SN2007, 5), 4: eksaktIndeks(sn.SN2007, 4) },
  SN2025: { 5: eksaktIndeks(sn.SN2025, 5), 4: eksaktIndeks(sn.SN2025, 4) },
};
const flat = [];
for (const std of ["SN2007", "SN2025"])
  for (const r of sn[std]) if (Number(r.niva) === 5) flat.push({ std, kode: r.kode, navn: r.navn, s: skarp(r.navn) });

// T6 — manuelle tilordninger. Hver rad har en begrunnelse som kan etterprøves
// mot Klass-uttrekket i data/. Ingen av dem er byggrelevante.
const MANUELL = {
  "Butikkhandel med kjæledyr og fôr til kjæledyr": {
    std: "SN2007", kode: "47.762",
    grunn: "Brønnøysund skriver «fôr», SSB Klass 47.762 skriver «fôrvarer»; ellers identisk streng og eneste kandidat under 47.76.",
  },
  "Tjenester tilknyttet hav- og kystbasert fiskeoppdrett": {
    std: "SN2007", kode: "03.213",
    grunn: "Brønnøysund skriver «fiskeoppdrett», SSB Klass 03.213 skriver «akvakultur»; samme næring, eneste tjenestekode under 03.21.",
  },
  "Produksjon av matfisk og skalldyr i hav- og kystbasert fiske": {
    std: "SN2007", kode: "03.211",
    grunn: "Avkortet ved 60 tegn; tilsvarer 03.211 «Produksjon av matfisk, bløtdyr, krepsdyr og pigghuder i hav- og kystbasert akvakultur».",
  },
  "Produksjon av matfisk og skalldyr i ferskvannsbasert fiskeop": {
    std: "SN2007", kode: "03.221",
    grunn: "Avkortet ved 60 tegn; ferskvannsparallellen til 03.211, dvs. 03.221 under 03.22 «Ferskvannsbasert akvakultur».",
  },
  "Investeringsselskaper og lignende lukket for allmennheten": {
    std: null, kode: null,
    grunn: "Navn fra en tidligere utgave av SN2007 (før AIF-omleggingen av 64.30). Finnes ikke i Klass versjon 30 slik den står i dag. Ikke byggrelevant; beholdes i «øvrige» uten kode.",
  },
};
const IKKE_NAERING = new Set(["Uoppgitt", "Enheten er slettet"]);

// ---------------- etiketter fra databasen ----------------
const rader = (await q(`
  select trim(bransje) as etikett,
         count(distinct orgnr) as selskaper,
         min(dato)::text as forste_dato,
         max(dato)::text as siste_dato,
         count(distinct orgnr) filter (where dato <  date '${SEAM}') as selsk_for_som,
         count(distinct orgnr) filter (where dato >= date '${SEAM}') as selsk_etter_som
  from kunngjoring.insolvens
  where type = 'Konkurs - åpning' and nullif(trim(bransje),'') is not null
  group by 1 order by 2 desc
`)).rows;

const stats = { T1: 0, T2: 0, T3: 0, T5: 0, T6: 0, IKKE_NAERING: 0, INGEN: 0 };
const kart = [];

for (const e of rader) {
  const rå = nfc(e.etikett);
  const flerbransje = /\n/.test(e.etikett);
  const primær = key60(e.etikett.split("\n")[0]);
  const forSom = Number(e.selsk_for_som) > 0, etterSom = Number(e.selsk_etter_som) > 0;
  const vintage = forSom && etterSom ? "begge" : etterSom ? "SN2025" : "SN2007";
  const prefStd = vintage === "SN2025" ? ["SN2025", "SN2007"] : ["SN2007", "SN2025"];

  let metode = null, treff = null, std = null;

  if (IKKE_NAERING.has(rå)) { metode = "IKKE_NAERING"; }

  if (!metode) for (const s of prefStd) { const t = idx[s][5].get(primær); if (t) { treff = t; std = s; metode = s === "SN2007" ? "T1" : "T2"; break; } }
  if (!metode) for (const s of prefStd) { const t = idx[s][4].get(primær); if (t) { treff = t; std = s; metode = "T3"; break; } }

  if (!metode) {
    const kandidater = [];
    const sk = skarp(primær);
    if (sk.length >= MIN_PREFIX) {
      for (const f of flat) {
        if (f.s === sk || f.s.startsWith(sk) || sk.startsWith(f.s)) {
          if (Math.min(f.s.length, sk.length) >= MIN_PREFIX) kandidater.push(f);
        }
      }
    }
    let koder = [...new Set(kandidater.map((k) => k.kode))];
    let pool = kandidater;
    if (koder.length > 1) {
      // flertydig på tvers av standardene: la vintagen avgjøre
      const iPref = kandidater.filter((k) => k.std === prefStd[0]);
      if ([...new Set(iPref.map((k) => k.kode))].length === 1) { pool = iPref; koder = [iPref[0].kode]; }
    }
    if (koder.length === 1) {
      const valgt = pool.find((k) => k.std === prefStd[0]) ?? pool[0];
      treff = { kode: valgt.kode, navn: valgt.navn, niva: 5 }; std = valgt.std; metode = "T5";
    }
  }

  if (!metode && MANUELL[rå]) {
    const m = MANUELL[rå];
    if (m.kode) { treff = { kode: m.kode, navn: "(manuelt tilordnet)", niva: 5 }; std = m.std; }
    metode = "T6";
  }

  if (!metode) metode = "INGEN";
  stats[metode]++;

  // kanonisk SN2007-kode
  let kanon = null, kanonNavn = null, kanonKilde = null;
  if (std === "SN2007" && treff) { kanon = treff.kode; kanonNavn = treff.navn; kanonKilde = "direkte SN2007"; }
  else if (std === "SN2025" && treff) {
    const g = korrMap.get(treff.kode) || [];
    if (g.length === 1) { kanon = g[0].kode; kanonNavn = g[0].navn; kanonKilde = "korrespondanse 1:1"; }
    else if (g.length > 1) { kanon = g.map((x) => x.kode).sort().join("|"); kanonNavn = g.map((x) => x.navn).join(" | "); kanonKilde = "korrespondanse 1:n"; }
    else {
      // Korrespondansetabell 2919 lister bare koder som ER endret (1 034 av 1 785).
      // Er koden uendret finnes den med samme kodestreng i SN2007 -> identitet.
      const iSn2007 = sn.SN2007.find((r) => r.kode === treff.kode);
      if (iSn2007) { kanon = iSn2007.kode; kanonNavn = iSn2007.navn; kanonKilde = "identisk kode i begge standarder"; }
    }
  }

  const erBygg = (k) => /^4[123]/.test(k || "");
  const koderKanon = kanon ? kanon.split("|") : [];
  kart.push({
    etikett: e.etikett,
    flerbransje,
    primaernaering: flerbransje ? primær : null,
    selskaper: Number(e.selskaper),
    forste_dato: e.forste_dato, siste_dato: e.siste_dato,
    selsk_for_som: Number(e.selsk_for_som), selsk_etter_som: Number(e.selsk_etter_som),
    vintage, metode, standard: std,
    kode: treff?.kode ?? null, kodenavn: treff?.navn ?? null, kodeniva: treff?.niva ?? null,
    kanonisk_sn2007: kanon, kanonisk_navn: kanonNavn, kanonisk_kilde: kanonKilde,
    naering2: koderKanon.length ? [...new Set(koderKanon.map((k) => k.slice(0, 2)))].sort().join("|") : null,
    er_bygg_F: koderKanon.length ? koderKanon.some(erBygg) : null,
    er_bygg_kjerne: koderKanon.length ? koderKanon.some((k) => /^(41\.2|42|43)/.test(k)) : null,
    er_eiendomsutvikling_41_1: koderKanon.length ? koderKanon.some((k) => /^41\.1/.test(k)) : null,
    manuell_grunn: MANUELL[rå]?.grunn ?? null,
  });
}

const sum = (f) => kart.filter(f).reduce((s, r) => s + r.selskaper, 0);
const rapport = {
  kjoredato: RUN_DATE,
  antall_etiketter: kart.length,
  selskaper_totalt: sum(() => true),
  metodefordeling: stats,
  selskaper_per_metode: Object.fromEntries(Object.keys(stats).map((m) => [m, sum((r) => r.metode === m)])),
  selskaper_med_kanonisk_kode: sum((r) => r.kanonisk_sn2007),
  andel_kanonisert_pst: (100 * sum((r) => r.kanonisk_sn2007)) / sum(() => true),
  ikke_naering: {
    etiketter: kart.filter((r) => r.metode === "IKKE_NAERING").map((r) => ({ etikett: r.etikett, selskaper: r.selskaper })),
    selskaper: sum((r) => r.metode === "IKKE_NAERING"),
  },
  uten_kode: kart.filter((r) => !r.kanonisk_sn2007 && r.metode !== "IKKE_NAERING")
    .map((r) => ({ etikett: r.etikett, selskaper: r.selskaper, metode: r.metode })),
  flerbransje: { etiketter: kart.filter((r) => r.flerbransje).length, selskaper: sum((r) => r.flerbransje) },
  bygg_F: { etiketter: kart.filter((r) => r.er_bygg_F).length, selskaper: sum((r) => r.er_bygg_F) },
  bygg_kjerne: { etiketter: kart.filter((r) => r.er_bygg_kjerne).length, selskaper: sum((r) => r.er_bygg_kjerne) },
  eiendomsutvikling_41_1: { etiketter: kart.filter((r) => r.er_eiendomsutvikling_41_1).length, selskaper: sum((r) => r.er_eiendomsutvikling_41_1) },
  t5_treff: kart.filter((r) => r.metode === "T5").map((r) => ({ etikett: r.etikett, selskaper: r.selskaper, kode: r.kode, kodenavn: r.kodenavn, standard: r.standard })),
};

const csv = writeCsv(`data/bransjekart-v3_${RUN_DATE}.csv`,
  ["etikett", "flerbransje", "primaernaering", "selskaper", "forste_dato", "siste_dato",
   "selsk_for_som", "selsk_etter_som", "vintage", "metode", "standard", "kode", "kodenavn", "kodeniva",
   "kanonisk_sn2007", "kanonisk_navn", "kanonisk_kilde", "naering2", "er_bygg_F", "er_bygg_kjerne",
   "er_eiendomsutvikling_41_1", "manuell_grunn"],
  kart.map((r) => [r.etikett.replace(/\n/g, " \\n "), r.flerbransje, r.primaernaering ?? "", r.selskaper,
    r.forste_dato, r.siste_dato, r.selsk_for_som, r.selsk_etter_som, r.vintage, r.metode, r.standard ?? "",
    r.kode ?? "", r.kodenavn ?? "", r.kodeniva ?? "", r.kanonisk_sn2007 ?? "", r.kanonisk_navn ?? "",
    r.kanonisk_kilde ?? "", r.naering2 ?? "", r.er_bygg_F ?? "", r.er_bygg_kjerne ?? "",
    r.er_eiendomsutvikling_41_1 ?? "", r.manuell_grunn ?? ""]));

const js = writeJson(`data/bransjekart-v3_${RUN_DATE}.json`, {
  versjon: "v3", kjoredato: RUN_DATE, som_dato: SEAM,
  beskrivelse: "Bransje-etikett på konkursåpningsraden (avkortet ved 60 tegn i kilden) -> NACE, begge klassifikasjonsvintager, kanonisert til SN2007 femsifret kode.",
  kilder: {
    sn2007: "https://data.ssb.no/api/klass/v1/versions/30",
    sn2025: "https://data.ssb.no/api/klass/v1/versions/3218",
    korrespondanse_sn2025_sn2007: "https://data.ssb.no/api/klass/v1/correspondencetables/2919",
  },
  rapport, kart,
});

console.log(JSON.stringify({ ...rapport, csv, js }, null, 2));
await done();
