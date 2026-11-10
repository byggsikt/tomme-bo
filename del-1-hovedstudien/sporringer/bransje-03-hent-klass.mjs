// bransje-03: hent SSBs offisielle kodelister (Klass-API) for SN2007 (versjon 30)
// og SN2025 (versjon 3218), samt korrespondansetabeller mellom dem.
// Klassifikasjon 6 = «Standard for næringsgruppering (SN)» — bekreftet mot
// https://data.ssb.no/api/klass/v1/classifications/6 den 2026-08-30.
// Ingen databasetilgang her; kun offentlig API. Lagrer rå JSON i data/.
import { writeJson, writeCsv, RUN_DATE } from "./_lib.mjs";

const BASE = "https://data.ssb.no/api/klass/v1";

async function getJson(url) {
  const r = await fetch(url, { headers: { Accept: "application/json" } });
  if (!r.ok) throw new Error(`${url} -> HTTP ${r.status}`);
  return r.json();
}

const out = { hentet: RUN_DATE, kilder: [] };

for (const [navn, vid] of [["SN2007", 30], ["SN2025", 3218]]) {
  const url = `${BASE}/versions/${vid}`;
  const v = await getJson(url);
  const items = v.classificationItems || [];
  out.kilder.push({
    standard: navn,
    versjon_id: vid,
    url,
    navn: v.name,
    gyldig_fra: v.validFrom,
    gyldig_til: v.validTo ?? null,
    antall_koder: items.length,
    korrespondanser: (v.correspondenceTables || []).map((c) => ({
      navn: c.name,
      kilde: c.source,
      mal: c.target,
      href: c._links?.self?.href ?? null,
    })),
  });
  const saved = writeJson(`data/klass-${navn}-versjon${vid}_${RUN_DATE}.json`, {
    hentet: RUN_DATE,
    url,
    navn: v.name,
    gyldig_fra: v.validFrom,
    koder: items.map((i) => ({
      kode: i.code,
      navn: i.name,
      niva: i.level,
      forelder: i.parentCode ?? null,
      kortnavn: i.shortName ?? null,
    })),
  });
  out[`fil_${navn}`] = saved;

  // Flat CSV med 5-sifret nivå (nivå 5) samt alle nivåer, for oppslag
  const csv = writeCsv(
    `data/klass-${navn}-koder_${RUN_DATE}.csv`,
    ["standard", "versjon_id", "kode", "navn", "niva", "forelder"],
    items.map((i) => [navn, vid, i.code, i.name, i.level, i.parentCode ?? ""])
  );
  out[`csv_${navn}`] = csv;
}

console.log(JSON.stringify(out, null, 2));
