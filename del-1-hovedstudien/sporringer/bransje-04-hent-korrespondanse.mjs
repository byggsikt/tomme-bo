// bransje-04: hent SSBs offisielle korrespondansetabell SN2025 -> SN2007 (id 2919).
// Dette er broen over sømmen i L17. Ingen databasetilgang; kun offentlig API.
import { writeJson, writeCsv, RUN_DATE } from "./_lib.mjs";

const URL = "https://data.ssb.no/api/klass/v1/correspondencetables/2919";

const r = await fetch(URL, { headers: { Accept: "application/json" } });
if (!r.ok) throw new Error(`HTTP ${r.status}`);
const c = await r.json();

const maps = c.correspondenceMaps || [];
const saved = writeJson(`data/klass-korrespondanse-SN2025-SN2007_${RUN_DATE}.json`, {
  hentet: RUN_DATE,
  url: URL,
  navn: c.name,
  kilde: c.source,
  mal: c.target,
  gyldig_fra: c.validFrom ?? null,
  antall_par: maps.length,
  par: maps,
});

const csv = writeCsv(
  `data/klass-korrespondanse-SN2025-SN2007_${RUN_DATE}.csv`,
  ["sn2025_kode", "sn2025_navn", "sn2007_kode", "sn2007_navn"],
  maps.map((m) => [m.sourceCode, m.sourceName, m.targetCode, m.targetName])
);

// Byggrelevante par (41/42/43 på begge sider)
const bygg = maps.filter(
  (m) => /^4[123]/.test(m.sourceCode || "") || /^4[123]/.test(m.targetCode || "")
);

console.log(JSON.stringify({
  navn: c.name, kilde: c.source, mal: c.target, url: URL,
  antall_par: maps.length, bygg_par: bygg.length, fil: saved, csv,
  bygg: bygg.map((m) => `${m.sourceCode} ${m.sourceName}  ->  ${m.targetCode} ${m.targetName}`),
}, null, 2));
