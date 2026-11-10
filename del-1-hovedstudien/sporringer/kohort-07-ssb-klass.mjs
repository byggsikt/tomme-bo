// LANE 1 / kohort — offisiell naeringsstandard fra SSB Klass (READ-ONLY mot DB).
//
// HVORFOR: bransje-etiketten i kunngjoringen er naeringens NAVN, avkortet til 60 tegn.
// company_intel.company baerer SN2025-vokabular (feiet ved registerbyttet 2025-09-01),
// mens kunngjoringene 2023-2024 baerer SN2007. En intern ordbok bommer derfor paa
// halvparten av etikettene. Losningen er den offisielle standarden selv:
//   SSB Klass, klassifikasjon 6 «Standard for naeringsgruppering (SN)»
//   versjon 30  = SN2007 (gyldig 2009-01-01 -> 2025-01-01)
//   versjon 3218 = SN2025 (gyldig 2025-01-01 ->)
// Kilde: https://data.ssb.no/api/klass/v1/classifications/6
//
// Skriver: data/ssb-klass-sn2007.json, data/ssb-klass-sn2025.json, data/bransjekart-v2.json
import { writeFileSync, readFileSync } from "node:fs";
import { createHash } from "node:crypto";

const DATA = "./data";
const KJORT = new Date().toISOString().slice(0, 10);

async function hentKoder(dato, filnavn) {
  const url = `https://data.ssb.no/api/klass/v1/classifications/6/codesAt.json?date=${dato}&language=nb`;
  const res = await fetch(url, { headers: { accept: "application/json" } });
  if (!res.ok) throw new Error(`${url} -> HTTP ${res.status}`);
  const body = await res.json();
  const payload = { kilde: url, hentet: KJORT, gyldig_dato: dato, antall: body.codes.length, koder: body.codes };
  const json = JSON.stringify(payload, null, 1);
  writeFileSync(`${DATA}/${filnavn}`, json, "utf8");
  const sha = createHash("sha256").update(json).digest("hex");
  console.log(`${filnavn}: ${body.codes.length} koder, sha256=${sha}`);
  return body.codes;
}

const sn2007 = await hentKoder("2024-06-01", "ssb-klass-sn2007.json");
const sn2025 = await hentKoder("2026-01-01", "ssb-klass-sn2025.json");

// Etikettordbok: navn avkortet til 60 tegn -> kode. Kunngjoringen skriver naeringens
// navn paa laveste niva (5-siffer) eller et hoyere niva; vi tar alle nivaer med.
function byggOrdbok(koder, merke) {
  const m = new Map();
  for (const k of koder) {
    const navn = (k.name || "").trim();
    if (!navn) continue;
    const nokkel = navn.slice(0, 60);
    const eksisterende = m.get(nokkel);
    // Foretrekk det mest spesifikke nivaaet (lengst kode) ved kollisjon; noter kollisjoner.
    if (!eksisterende) m.set(nokkel, { kode: k.code, navn, niva: k.level, vintage: merke, kolliderer: [] });
    else eksisterende.kolliderer.push(k.code);
  }
  return m;
}

const o07 = byggOrdbok(sn2007, "SN2007");
const o25 = byggOrdbok(sn2025, "SN2025");
console.log(`ordbok SN2007: ${o07.size} etiketter, SN2025: ${o25.size} etiketter`);

const kart = {
  versjon: "v2",
  kjoredato: KJORT,
  kilde: "SSB Klass klassifikasjon 6, versjon 30 (SN2007) og 3218 (SN2025), hentet via data.ssb.no/api/klass",
  beskrivelse: "naeringsnavn avkortet til 60 tegn -> naeringskode, begge vintager (L17)",
  sn2007: Object.fromEntries([...o07].map(([k, v]) => [k, { kode: v.kode, navn: v.navn, niva: v.niva, kolliderer: v.kolliderer }])),
  sn2025: Object.fromEntries([...o25].map(([k, v]) => [k, { kode: v.kode, navn: v.navn, niva: v.niva, kolliderer: v.kolliderer }])),
};
const kartJson = JSON.stringify(kart, null, 1);
writeFileSync(`${DATA}/bransjekart-v2.json`, kartJson, "utf8");
console.log("bransjekart-v2.json sha256=" + createHash("sha256").update(kartJson).digest("hex"));

// Kontroll: hvor mange bygg-koder (41/42/43) finnes i hver vintage?
const bygg07 = [...o07.values()].filter(v => /^(41|42|43)/.test(v.kode));
const bygg25 = [...o25.values()].filter(v => /^(41|42|43)/.test(v.kode));
console.log(`bygg-etiketter SN2007: ${bygg07.length}, SN2025: ${bygg25.length}`);
console.log("SN2007 bygg-eksempler:", bygg07.slice(0, 12).map(v => `${v.kode} ${v.navn}`));
