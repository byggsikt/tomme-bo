// LANE 1 / kohort — SSB-KALIBRERING (READ-ONLY mot DB; POST-spørring mot SSBs aapne API).
//
// Vaart materiale er AS/ASA-forankret. SSB eier universet av konkursaapninger; vi eier
// utfallet av boet. Denne tabellen viser presist hvor mye av SSBs univers vi ser, per
// kvartal, i alt og for bygge- og anleggsvirksomhet.
//
// Kilder (verifisert 2026-08-30):
//   tabell 07165  Konkurser, etter region, naering (SN2007), organisasjonsform ... og kvartal
//                 https://data.ssb.no/api/v0/no/table/07165
//                 -> gir AS + ASA separat, og naering paa tosifret niva (41/42/43)
//   tabell 09122  Opna konkursar, etter naering, konkurstype ... og kvartal
//                 https://data.ssb.no/api/v0/no/table/09122
//                 -> gir «Foretakskonkursar ekskl. einskildpersonforetak» og naeringsomraade F
import { getPool, closePool } from "./db.mjs";
import { writeFileSync } from "node:fs";
import { createHash } from "node:crypto";
import { slaaOpp, erByggF } from "./kohort-bransjeklassifikator.mjs";

const DATA = "./data";
const KJORT = new Date().toISOString().slice(0, 10);
const KVARTALER = [];
for (let aa = 2023; aa <= 2026; aa++) for (let k = 1; k <= 4; k++) {
  const s = `${aa}K${k}`;
  if (s >= "2023K3" && s <= "2026K2") KVARTALER.push(s);
}
const pool = getPool();
const sha = (s) => createHash("sha256").update(s).digest("hex");
const out = (l, r) => { console.log("\n=== " + l + " ==="); console.log(JSON.stringify(r, null, 1)); };

async function px(tabell, query) {
  const url = `https://data.ssb.no/api/v0/no/table/${tabell}`;
  const res = await fetch(url, {
    method: "POST", headers: { "content-type": "application/json" },
    body: JSON.stringify({ query, response: { format: "json-stat2" } }),
  });
  if (!res.ok) throw new Error(`${tabell} -> HTTP ${res.status}: ${(await res.text()).slice(0, 300)}`);
  return { url, data: await res.json() };
}
// json-stat2 -> flat oppslag paa dimensjonsverdier
function flat(js) {
  const dims = js.id, sizes = js.size;
  const kat = dims.map(d => Object.keys(js.dimension[d].category.index)
    .sort((a, b) => js.dimension[d].category.index[a] - js.dimension[d].category.index[b]));
  const ut = new Map();
  const n = sizes.reduce((a, b) => a * b, 1);
  for (let i = 0; i < n; i++) {
    let rest = i; const nokkel = [];
    for (let d = sizes.length - 1; d >= 0; d--) { nokkel[d] = kat[d][rest % sizes[d]]; rest = Math.floor(rest / sizes[d]); }
    ut.set(nokkel.join("|"), js.value[i]);
  }
  return ut;
}

try {
  await pool.query("set statement_timeout = '900s'");

  // ---- SSB 07165: AS + ASA, hele landet, naering 41/42/43 og totalt
  const r07165 = await px("07165", [
    { code: "Region", selection: { filter: "item", values: ["0"] } },
    { code: "NACE2007", selection: { filter: "item", values: ["01-99", "41", "42", "43"] } },
    { code: "OrgFormer", selection: { filter: "item", values: ["99", "03", "04"] } },
    { code: "Tid", selection: { filter: "item", values: KVARTALER } },
  ]);
  const f7 = flat(r07165.data);
  const g7 = (nace, org, kv) => f7.get(["0", nace, org, "Konkurser", kv].join("|")) ?? null;

  // ---- SSB 09122: alle / foretakskonkursar ekskl. ENK, naeringsomraade F og A-Z
  const r09122 = await px("09122", [
    { code: "Naring", selection: { filter: "item", values: ["A-Z", "F"] } },
    { code: "Konkurstypar", selection: { filter: "item", values: ["00", "11"] } },
    { code: "ContentsCode", selection: { filter: "item", values: ["Konkursar"] } },
    { code: "Tid", selection: { filter: "item", values: KVARTALER } },
  ]);
  const f9 = flat(r09122.data);
  const g9 = (nar, typ, kv) => f9.get([nar, typ, "Konkursar", kv].join("|")) ?? null;

  // ---- VAART: forste konkursaapning per selskap, per kvartal
  const rader = (await pool.query(`
    with aapning as materialized (
      select orgnr, min(dato) as d from kunngjoring.insolvens where type='Konkurs - åpning' group by orgnr
    ),
    attr as materialized (
      select i.orgnr, nullif(trim(i.bransje),'') as bransje
      from kunngjoring.insolvens i join aapning a on a.orgnr=i.orgnr and i.dato=a.d
      where i.type='Konkurs - åpning'
    )
    select to_char(a.d,'YYYY') || 'K' || to_char(a.d,'Q') as kvartal, at.bransje
    from aapning a left join attr at on at.orgnr = a.orgnr
    where a.d >= date '2023-07-01'
  `)).rows;
  const vaart = new Map();
  for (const r of rader) {
    const e = vaart.get(r.kvartal) || { alle: 0, bygg: 0 };
    e.alle++; if (erByggF(slaaOpp(r.bransje).kode)) e.bygg++;
    vaart.set(r.kvartal, e);
  }

  const tab = KVARTALER.map(kv => {
    const v = vaart.get(kv) || { alle: 0, bygg: 0 };
    const ssbAS = (g7("01-99", "03", kv) ?? 0) + (g7("01-99", "04", kv) ?? 0);
    const ssbASbygg = ["41", "42", "43"].reduce((a, n) =>
      a + (g7(n, "03", kv) ?? 0) + (g7(n, "04", kv) ?? 0), 0);
    return {
      kvartal: kv,
      vaart_aapninger: v.alle,
      ssb_07165_AS_ASA: ssbAS,
      dekning_AS_ASA_pst: ssbAS ? +(100 * v.alle / ssbAS).toFixed(1) : null,
      ssb_07165_alle_orgformer: g7("01-99", "99", kv),
      dekning_alle_orgformer_pst: g7("01-99", "99", kv) ? +(100 * v.alle / g7("01-99", "99", kv)).toFixed(1) : null,
      ssb_09122_foretakskonkurser: g9("A-Z", "11", kv),
      ssb_09122_alle_konkurser: g9("A-Z", "00", kv),
      vaart_bygg_F: v.bygg,
      ssb_07165_AS_ASA_bygg_41_43: ssbASbygg,
      dekning_bygg_pst: ssbASbygg ? +(100 * v.bygg / ssbASbygg).toFixed(1) : null,
      ssb_09122_bygg_F_foretak: g9("F", "11", kv),
    };
  });
  out("SSB-KALIBRERING 2023K3-2026K2", tab);

  const sum = (k) => tab.reduce((a, r) => a + (r[k] ?? 0), 0);
  out("samlet over hele perioden", {
    vaart_aapninger: sum("vaart_aapninger"),
    ssb_AS_ASA: sum("ssb_07165_AS_ASA"),
    dekning_AS_ASA_pst: +(100 * sum("vaart_aapninger") / sum("ssb_07165_AS_ASA")).toFixed(1),
    ssb_alle_orgformer: sum("ssb_07165_alle_orgformer"),
    dekning_alle_orgformer_pst: +(100 * sum("vaart_aapninger") / sum("ssb_07165_alle_orgformer")).toFixed(1),
    vaart_bygg: sum("vaart_bygg_F"),
    ssb_AS_ASA_bygg: sum("ssb_07165_AS_ASA_bygg_41_43"),
    dekning_bygg_pst: +(100 * sum("vaart_bygg_F") / sum("ssb_07165_AS_ASA_bygg_41_43")).toFixed(1),
  });

  const kol = Object.keys(tab[0]);
  const csv = [kol.join(";"), ...tab.map(r => kol.map(k => r[k] ?? "").join(";"))].join("\n") + "\n";
  writeFileSync(`${DATA}/ssb-kalibrering-${KJORT}.csv`, csv, "utf8");
  const meta = { kjoredato: KJORT, kilder: [r07165.url, r09122.url],
                 tabeller: ["07165 Konkurser, etter region, næring (SN2007), organisasjonsform, statistikkvariabel og kvartal",
                            "09122 Opna konkursar, etter næring, konkurstype, statistikkvariabel og kvartal"],
                 merknad: "Vaart materiale er AS/ASA-forankret; SSB eier universet av aapninger, vi eier boets utfall.",
                 csv_sha256: sha(csv) };
  writeFileSync(`${DATA}/ssb-kalibrering-${KJORT}.json`, JSON.stringify(meta, null, 1), "utf8");
  console.log(`\nssb-kalibrering-${KJORT}.csv sha256=${sha(csv)}`);
} catch (e) { console.error("FEIL:", e.message, e.stack); } finally { await closePool(); }
