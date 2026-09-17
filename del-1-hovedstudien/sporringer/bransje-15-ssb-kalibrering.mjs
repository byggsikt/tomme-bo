// bransje-15: kalibrering av BRANSJEDIMENSJONEN mot offisiell statistikk.
// SSB tabell 09122 «Opna konkursar, etter næring, konkurstype, statistikkvariabel og kvartal»
// har næring på seksjonsnivå, der F = «Byggje- og anleggsverksemd» (NACE 41-43) og
// Z = «Ikkje opplyst». Det svarer nøyaktig til vår byggdefinisjon og vår «Uoppgitt»-bøtte.
// Konkurstype 11 = «Føretakskonkursar ekskl. einskildpersonføretak» er den relevante
// sammenlikningen: kunngjøringsmaterialet vårt er forankret i aksjeselskaper.
// Vi sammenlikner BYGGANDELEN av åpnede konkurser per kvartal — ikke nivået, som er
// dekningsavhengig — samt Z-andelen.
// READ-ONLY mot databasen; offentlig API mot SSB.
import { q, done, writeCsv, writeJson, RUN_DATE } from "./_lib.mjs";
import { readFileSync } from "node:fs";

const TABELL = "https://data.ssb.no/api/v0/no/table/09122";
const KVARTALER = [];
for (const aar of [2023, 2024, 2025]) for (const k of [1, 2, 3, 4]) KVARTALER.push(`${aar}K${k}`);
KVARTALER.push("2026K1", "2026K2");

async function ssb(konkurstype) {
  const body = {
    query: [
      { code: "Naring", selection: { filter: "item", values: ["A-Z", "F", "Z"] } },
      { code: "Konkurstypar", selection: { filter: "item", values: [konkurstype] } },
      { code: "ContentsCode", selection: { filter: "item", values: ["Konkursar"] } },
      { code: "Tid", selection: { filter: "item", values: KVARTALER } },
    ],
    response: { format: "json-stat2" },
  };
  const r = await fetch(TABELL, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) });
  if (!r.ok) throw new Error(`SSB HTTP ${r.status}: ${await r.text()}`);
  const j = await r.json();
  const dimOrder = j.id;
  const sizes = j.size;
  const idx = {};
  for (const d of dimOrder) idx[d] = Object.keys(j.dimension[d].category.index)
    .sort((a, b) => j.dimension[d].category.index[a] - j.dimension[d].category.index[b]);
  const ut = {};
  let n = 0;
  for (let i = 0; i < j.value.length; i++) {
    // radmajor over dimOrder
    let rest = i, koord = [];
    for (let d = dimOrder.length - 1; d >= 0; d--) { koord[d] = rest % sizes[d]; rest = Math.floor(rest / sizes[d]); }
    const nar = idx[dimOrder[dimOrder.indexOf("Naring")]][koord[dimOrder.indexOf("Naring")]];
    const tid = idx["Tid"][koord[dimOrder.indexOf("Tid")]];
    ut[`${nar}|${tid}`] = j.value[i];
    n++;
  }
  return { celler: n, verdier: ut, kilde: `${TABELL} (json-stat2, konkurstype ${konkurstype})`, oppdatert: j.updated };
}

const ssb00 = await ssb("00");
const ssb11 = await ssb("11");

// ---- vårt materiale, samme kvartaler ----
const DATA = "./data";
const kartJson = JSON.parse(readFileSync(`${DATA}/bransjekart-v3_${RUN_DATE}.json`, "utf8"));
const kart = new Map(kartJson.kart.map((r) => [r.etikett.normalize("NFC"), r]));

const vaare = (await q(`
  with apn as materialized (
    select orgnr, min(dato) as forste, max(nullif(trim(bransje),'')) as etikett
    from kunngjoring.insolvens where type = 'Konkurs - åpning' group by orgnr
  )
  select to_char(forste, 'YYYY') || 'K' || to_char(extract(quarter from forste), 'FM9') as kvartal,
         etikett, count(*) as n
  from apn where forste >= date '2023-01-01' group by 1, 2
`)).rows;

const mine = {};
for (const r of vaare) {
  const k = kart.get((r.etikett ?? "").normalize("NFC"));
  const b = (mine[r.kvartal] ??= { alle: 0, bygg: 0, uoppgitt: 0 });
  const n = Number(r.n);
  b.alle += n;
  if (k?.er_bygg_F) b.bygg += n;
  if (k?.metode === "IKKE_NAERING") b.uoppgitt += n;
}

const rows = [];
for (const kv of KVARTALER) {
  const s0 = ssb00.verdier, s1 = ssb11.verdier;
  const m = mine[kv] ?? { alle: 0, bygg: 0, uoppgitt: 0 };
  const ssbAlle11 = s1[`A-Z|${kv}`], ssbBygg11 = s1[`F|${kv}`], ssbZ11 = s1[`Z|${kv}`];
  const ssbAlle00 = s0[`A-Z|${kv}`], ssbBygg00 = s0[`F|${kv}`];
  rows.push({
    kvartal: kv,
    ssb_alle_foretakskonkurser: ssbAlle11, ssb_bygg_foretakskonkurser: ssbBygg11, ssb_ikke_opplyst: ssbZ11,
    ssb_byggandel_pst: ssbAlle11 ? (100 * ssbBygg11) / ssbAlle11 : null,
    ssb_alle_alle_typer: ssbAlle00, ssb_bygg_alle_typer: ssbBygg00,
    vaar_alle: m.alle, vaar_bygg: m.bygg, vaar_uoppgitt: m.uoppgitt,
    vaar_byggandel_pst: m.alle ? (100 * m.bygg) / m.alle : null,
    dekning_alle_pst: ssbAlle11 ? (100 * m.alle) / ssbAlle11 : null,
    dekning_bygg_pst: ssbBygg11 ? (100 * m.bygg) / ssbBygg11 : null,
  });
}

const f = (x, d = 1) => (x === null || x === undefined ? "" : Number(x).toFixed(d));
const csv = writeCsv(`figurer/F5-ssb-kalibrering-bransje_${RUN_DATE}.csv`,
  ["kvartal", "ssb_foretakskonkurser_alle", "ssb_foretakskonkurser_bygg", "ssb_ikke_opplyst",
   "ssb_byggandel_pst", "vaart_materiale_alle", "vaart_materiale_bygg", "vaart_materiale_uoppgitt",
   "vaar_byggandel_pst", "dekning_alle_pst", "dekning_bygg_pst"],
  rows.map((r) => [r.kvartal, r.ssb_alle_foretakskonkurser, r.ssb_bygg_foretakskonkurser, r.ssb_ikke_opplyst,
    f(r.ssb_byggandel_pst), r.vaar_alle, r.vaar_bygg, r.vaar_uoppgitt, f(r.vaar_byggandel_pst),
    f(r.dekning_alle_pst), f(r.dekning_bygg_pst)]));

// kohortkvartalene (fulle kvartaler innenfor 2023-09-01..2024-12-31 er 2023K4..2024K4)
const kohortKv = ["2023K4", "2024K1", "2024K2", "2024K3", "2024K4"];
const agg = (sel) => kohortKv.reduce((s, kv) => s + (sel(rows.find((r) => r.kvartal === kv)) ?? 0), 0);
const sammendrag = {
  kohortkvartaler: kohortKv,
  ssb_bygg: agg((r) => r.ssb_bygg_foretakskonkurser), ssb_alle: agg((r) => r.ssb_alle_foretakskonkurser),
  vaar_bygg: agg((r) => r.vaar_bygg), vaar_alle: agg((r) => r.vaar_alle),
  ssb_byggandel_pst: (100 * agg((r) => r.ssb_bygg_foretakskonkurser)) / agg((r) => r.ssb_alle_foretakskonkurser),
  vaar_byggandel_pst: (100 * agg((r) => r.vaar_bygg)) / agg((r) => r.vaar_alle),
  dekning_alle_pst: (100 * agg((r) => r.vaar_alle)) / agg((r) => r.ssb_alle_foretakskonkurser),
  dekning_bygg_pst: (100 * agg((r) => r.vaar_bygg)) / agg((r) => r.ssb_bygg_foretakskonkurser),
  ssb_ikke_opplyst: agg((r) => r.ssb_ikke_opplyst), vaar_uoppgitt: agg((r) => r.vaar_uoppgitt),
};

const js = writeJson(`data/bransje-ssb-kalibrering_${RUN_DATE}.json`, {
  kjoredato: RUN_DATE, kilde: TABELL, ssb_oppdatert: ssb11.oppdatert,
  merknad: "Konkurstype 11 = føretakskonkursar ekskl. einskildpersonføretak. Nivået i vårt materiale er dekningsavhengig; det er BYGGANDELEN som kalibreres.",
  rader: rows, sammendrag,
});

console.log(JSON.stringify({ ssb_oppdatert: ssb11.oppdatert, sammendrag, csv, js,
  tabell: rows.filter((r) => r.ssb_alle_foretakskonkurser != null).map((r) =>
    `${r.kvartal}  SSB alle=${r.ssb_alle_foretakskonkurser} bygg=${r.ssb_bygg_foretakskonkurser} (${f(r.ssb_byggandel_pst)}%)  |  vårt alle=${r.vaar_alle} bygg=${r.vaar_bygg} (${f(r.vaar_byggandel_pst)}%)  |  dekning alle ${f(r.dekning_alle_pst)}% bygg ${f(r.dekning_bygg_pst)}%`),
}, null, 2));
await done();
