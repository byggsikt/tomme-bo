// DATAKONTROLLØREN — SSB-kalibrering, uavhengig rekjøring.
// (a) 07165: AS+ASA-åpninger 2023K3..2026K2 mot våre første åpninger per kvartal.
// (b) 09122: 2026K2-ankeret (950 alle / 237 bygg, konkurstype 00) og
//     foretakskonkursar ekskl. ENK (type 11) i de fem hele kohortkvartalene
//     2023K4..2024K4, totalt og næringsområde F, mot vårt materiale.
// READ-ONLY mot DB; POST mot data.ssb.no (åpent API).
import { getPool, closePool } from "./db.mjs";
import { readFileSync } from "node:fs";

const DATA = "./data";
const v3 = new Map(JSON.parse(readFileSync(`${DATA}/bransjekart-v3_2026-08-30.json`, "utf8"))
  .kart.map(r => [r.etikett, r]));
const KV = [];
for (let a = 2023; a <= 2026; a++) for (let k = 1; k <= 4; k++) {
  const s = `${a}K${k}`; if (s >= "2023K3" && s <= "2026K2") KV.push(s);
}
async function px(tab, query) {
  const res = await fetch(`https://data.ssb.no/api/v0/no/table/${tab}`, {
    method: "POST", headers: { "content-type": "application/json" },
    body: JSON.stringify({ query, response: { format: "json-stat2" } }),
  });
  if (!res.ok) throw new Error(`${tab} HTTP ${res.status}`);
  return res.json();
}
function flat(js) {
  const kat = js.id.map(d => Object.keys(js.dimension[d].category.index)
    .sort((a, b) => js.dimension[d].category.index[a] - js.dimension[d].category.index[b]));
  const ut = new Map(); const n = js.size.reduce((a, b) => a * b, 1);
  for (let i = 0; i < n; i++) {
    let rest = i; const nk = [];
    for (let d = js.size.length - 1; d >= 0; d--) { nk[d] = kat[d][rest % js.size[d]]; rest = Math.floor(rest / js.size[d]); }
    ut.set(nk.join("|"), js.value[i]);
  }
  return ut;
}
const pool = getPool();
try {
  await pool.query("set statement_timeout = '600s'");
  const vaare = (await pool.query(`
    with s as materialized (
      select orgnr, min(dato) filter (where type = 'Konkurs - åpning') as aapning
      from kunngjoring.insolvens group by orgnr
    )
    select to_char(s.aapning,'YYYY') || 'K' || to_char(s.aapning,'Q') as kvartal,
           count(*) as alle,
           count(*) filter (where exists (
             select 1 from kunngjoring.insolvens i
             where i.orgnr = s.orgnr and i.dato = s.aapning and i.type = 'Konkurs - åpning'
           )) as kontrollsum
    from s where s.aapning >= date '2023-07-01'
    group by 1 order by 1`)).rows;
  // bygg per kvartal trenger etikett -> hent åpningsradene
  const brader = (await pool.query(`
    with s as materialized (
      select orgnr, min(dato) filter (where type = 'Konkurs - åpning') as aapning
      from kunngjoring.insolvens group by orgnr
    )
    select to_char(s.aapning,'YYYY') || 'K' || to_char(s.aapning,'Q') as kvartal,
           split_part(nullif(trim(i.bransje),''), e'\n', 1) as etikett, count(*) as n
    from s join kunngjoring.insolvens i
      on i.orgnr = s.orgnr and i.dato = s.aapning and i.type = 'Konkurs - åpning'
    where s.aapning >= date '2023-07-01'
    group by 1, 2`)).rows;
  const byggKv = new Map();
  for (const r of brader) {
    const k = v3.get((r.etikett || "").trim());
    if (k && k.er_bygg_F === true)
      byggKv.set(r.kvartal, (byggKv.get(r.kvartal) || 0) + Number(r.n));
  }

  const f7 = flat(await px("07165", [
    { code: "Region", selection: { filter: "item", values: ["0"] } },
    { code: "NACE2007", selection: { filter: "item", values: ["01-99", "41", "42", "43"] } },
    { code: "OrgFormer", selection: { filter: "item", values: ["03", "04"] } },
    { code: "Tid", selection: { filter: "item", values: KV } },
  ]));
  const g7 = (nace, org, kv) => f7.get(["0", nace, org, "Konkurser", kv].join("|")) ?? 0;
  const f9 = flat(await px("09122", [
    { code: "Naring", selection: { filter: "item", values: ["A-Z", "F", "Z"] } },
    { code: "Konkurstypar", selection: { filter: "item", values: ["00", "11"] } },
    { code: "ContentsCode", selection: { filter: "item", values: ["Konkursar"] } },
    { code: "Tid", selection: { filter: "item", values: KV } },
  ]));
  const g9 = (nar, typ, kv) => f9.get([nar, typ, "Konkursar", kv].join("|")) ?? 0;

  let vSum = 0, sSum = 0, vB = 0, sB = 0;
  const perKv = [];
  for (const kv of KV) {
    const v = Number((vaare.find(r => r.kvartal === kv) || {}).alle || 0);
    const s = g7("01-99", "03", kv) + g7("01-99", "04", kv);
    const vb = byggKv.get(kv) || 0;
    const sb = ["41", "42", "43"].reduce((a, n) => a + g7(n, "03", kv) + g7(n, "04", kv), 0);
    vSum += v; sSum += s; vB += vb; sB += sb;
    perKv.push({ kvartal: kv, vaart: v, ssb_AS_ASA: s, dekning_pst: +(100 * v / s).toFixed(1) });
  }
  console.log(JSON.stringify({
    ssb_07165_AS_ASA_2023K3_2026K2: { vaart: vSum, ssb: sSum, dekning_pst: +(100 * vSum / sSum).toFixed(1),
      kvartal_min_pst: Math.min(...perKv.map(r => r.dekning_pst)),
      kvartal_maks_pst: Math.max(...perKv.map(r => r.dekning_pst)) },
    ssb_07165_bygg_41_43: { vaart: vB, ssb: sB, dekning_pst: +(100 * vB / sB).toFixed(1) },
    anker_09122_2026K2_type00: { alle: g9("A-Z", "00", "2026K2"), bygg_F: g9("F", "00", "2026K2") },
    kohortkvartal_09122_type11_2023K4_2024K4: (() => {
      const kvs = ["2023K4", "2024K1", "2024K2", "2024K3", "2024K4"];
      const ssbT = kvs.reduce((a, k) => a + g9("A-Z", "11", k), 0);
      const ssbF = kvs.reduce((a, k) => a + g9("F", "11", k), 0);
      const ssbZ = kvs.reduce((a, k) => a + g9("Z", "11", k), 0);
      const vT = kvs.reduce((a, k) => a + Number((vaare.find(r => r.kvartal === k) || {}).alle || 0), 0);
      const vF = kvs.reduce((a, k) => a + (byggKv.get(k) || 0), 0);
      return { ssb_totalt: ssbT, ssb_bygg_F: ssbF, ssb_ikkje_opplyst: ssbZ,
               vaart_totalt: vT, vaart_bygg_F: vF,
               byggandel_ssb_pst: +(100 * ssbF / ssbT).toFixed(2),
               byggandel_vaar_pst: +(100 * vF / vT).toFixed(2),
               dekning_totalt_pst: +(100 * vT / ssbT).toFixed(2),
               dekning_bygg_pst: +(100 * vF / ssbF).toFixed(2) };
    })(),
    per_kvartal: perKv,
  }, null, 1));
} catch (e) { console.error("FEIL:", e.message); process.exitCode = 1; }
finally { await closePool(); }
