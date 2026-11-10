// LANE 1 / kohort — hvorfor gir bygg 1 401 og ikke 1 142? (READ-ONLY)
// Reproduserer den gamle metoden (intern ordbok fra company.industry_text_1) mot den
// nye (offisiell SSB-standard) paa nøyaktig samme kohort.
import { getPool, closePool } from "./db.mjs";
import { readFileSync } from "node:fs";
import { slaaOpp, erByggF, erByggUtforende, IKKE_NAERING } from "./kohort-bransjeklassifikator.mjs";

const DATA = "./data";
const pool = getPool();
const out = (l, r) => { console.log("\n=== " + l + " ==="); console.log(JSON.stringify(r, null, 1)); };

try {
  await pool.query("set statement_timeout = '900s'");
  const rader = JSON.parse(readFileSync(DATA + "/_kohort-rader-arbeidskopi.json", "utf8"));

  // GAMMEL METODE: ordbok fra company.industry_text_1 (som er feiet til SN2025-vokabular)
  const gammel = new Map();
  for (const r of (await pool.query(`
    select left(industry_text_1,60) as etikett, industry_code_1 as kode, count(*) as n,
           row_number() over (partition by left(industry_text_1,60) order by count(*) desc, industry_code_1) as rn
    from company_intel.company
    where industry_code_1 is not null and industry_text_1 is not null
    group by 1,2
  `)).rows) if (Number(r.rn) === 1) gammel.set(r.etikett, r.kode);

  let g_bygg = 0, n_bygg = 0, n_byggU = 0, g_treff = 0, n_treff = 0;
  const kunNy = new Map(), kunGammel = new Map(), residual = new Map();
  for (const r of rader) {
    const gk = gammel.get((r.bransje || "").split("\n")[0]) || null;
    const ny = slaaOpp(r.bransje);
    r.nace = ny.kode; r.nace_kilde = ny.kilde; r.nace_vintage = ny.vintage || null;
    if (gk) g_treff++; if (ny.kode) n_treff++;
    const gB = !!gk && /^(41|42|43)/.test(gk), nB = erByggF(ny.kode);
    if (gB) g_bygg++; if (nB) n_bygg++; if (erByggUtforende(ny.kode)) n_byggU++;
    if (nB && !gB) kunNy.set(r.bransje, (kunNy.get(r.bransje) || 0) + 1);
    if (gB && !nB) kunGammel.set(r.bransje, (kunGammel.get(r.bransje) || 0) + 1);
    if (!ny.kode && !IKKE_NAERING.has((r.bransje || "").split("\n")[0].trim()))
      residual.set(r.bransje, (residual.get(r.bransje) || 0) + 1);
  }

  out("ordbok-treff paa kohorten (n=5165)", {
    gammel_intern_ordbok_treff: g_treff, ny_ssb_standard_treff: n_treff,
    gammel_bygg_41_43: g_bygg, ny_bygg_F_41_43: n_bygg, ny_bygg_utforende: n_byggU,
  });
  out("BYGG bare i den nye (SSB-)metoden — etiketter den interne ordboken bommet paa",
      [...kunNy].sort((a, b) => b[1] - a[1]).map(([e, n]) => ({ etikett: e, selskaper: n })));
  out("BYGG bare i den gamle metoden", [...kunGammel].map(([e, n]) => ({ etikett: e, selskaper: n })));
  out("uklassifiserte etiketter som IKKE er «Uoppgitt»/«Enheten er slettet»",
      [...residual].sort((a, b) => b[1] - a[1]).map(([e, n]) => ({ etikett: e, selskaper: n })));
  out("oppslagskilde-fordeling", Object.entries(
      rader.reduce((a, r) => (a[r.nace_kilde] = (a[r.nace_kilde] || 0) + 1, a), {})));
  out("vintage-fordeling (L17)", Object.entries(
      rader.reduce((a, r) => (a[r.nace_vintage || "-"] = (a[r.nace_vintage || "-"] || 0) + 1, a), {})));
} catch (e) { console.error("FEIL:", e.message, e.stack); } finally { await closePool(); }
