// bransje-09: bransjetabellen. Per kanonisk SN2007-kode: antall, innstillingsandel
// og eksakt Clopper-Pearson 95 %-KI. Celler med n < 10 undertrykkes i publiseringsuttrekket.
// Rangerer byggfagene mot hverandre OG mot de største ikke-byggnæringene.
// Måler også hvor mye den gamle kartmetoden (modal industry_code_1) undertelte bygg.
// READ-ONLY.
import { q, done, writeCsv, writeJson, clopperPearson, RUN_DATE } from "./_lib.mjs";
import { readFileSync } from "node:fs";

const DATA = "./data";
const kartRader = JSON.parse(readFileSync(`${DATA}/bransjekart-v3_${RUN_DATE}.json`, "utf8")).kart;
const kart = new Map(kartRader.map((r) => [r.etikett.normalize("NFC"), r]));

// v1-kartet (modal industry_code_1 i selskapsuniverset) — kun for å måle underdekningen
let v1 = new Map();
try {
  for (const r of JSON.parse(readFileSync(`${DATA}/bransjekart-v1.json`, "utf8")).kart)
    v1.set(r.etikett.normalize("NFC"), r.kode);
} catch { v1 = null; }

const VINDU = { start: "2023-09-01", slutt: "2024-12-31" };
const MODEN = { start: "2023-08-24", slutt: "2024-12-31" };

async function hentKohort(v) {
  return (await q(`
    with apn as materialized (
      select orgnr, min(dato) as forste_apning, max(nullif(trim(bransje),'')) as etikett
      from kunngjoring.insolvens where type = 'Konkurs - åpning' group by orgnr
    ),
    koh as materialized (
      select * from apn where forste_apning between date '${v.start}' and date '${v.slutt}'
    ),
    inn as materialized (
      select orgnr, min(dato) as dato from kunngjoring.insolvens
      where type ilike 'Konkurs - innstilling%' group by orgnr
    ),
    avs as materialized (
      select orgnr, min(dato) as dato from kunngjoring.insolvens
      where type ilike 'Konkurs - avslutning%' group by orgnr
    )
    select k.orgnr, k.forste_apning::text as apning, k.etikett,
           i.dato::text as innstilt, v2.dato::text as avsluttet
    from koh k left join inn i on i.orgnr = k.orgnr left join avs v2 on v2.orgnr = k.orgnr
  `)).rows;
}

const KOH = { hoved: await hentKohort(VINDU), moden: await hentKohort(MODEN) };

function grupper(rader, nokkel) {
  const g = new Map();
  for (const r of rader) {
    const k = r.etikett ? kart.get(r.etikett.normalize("NFC")) : null;
    const key = nokkel(r, k);
    if (key === null) continue;
    if (!g.has(key)) g.set(key, { n: 0, innstilt: 0, avsluttet: 0, apen: 0, kart: k });
    const b = g.get(key);
    b.n++;
    if (r.innstilt) b.innstilt++;
    else if (r.avsluttet) b.avsluttet++;
    else b.apen++;
  }
  return g;
}

function tabell(g, minN = 1) {
  const rows = [];
  for (const [key, b] of g) {
    if (b.n < minN) continue;
    const [lo, hi] = clopperPearson(b.innstilt, b.n);
    rows.push({
      nokkel: key, n: b.n, innstilt: b.innstilt, avsluttet: b.avsluttet, apen: b.apen,
      innstilt_pst: (100 * b.innstilt) / b.n,
      ki95_lav_pst: 100 * lo, ki95_hoy_pst: 100 * hi,
      apen_pst: (100 * b.apen) / b.n,
    });
  }
  return rows.sort((a, b) => b.innstilt_pst - a.innstilt_pst || b.n - a.n);
}

const out = { kjoredato: RUN_DATE };

// ---- 1. Byggfagene, moden kohort (som briefen) og hovedvindu ----
const byggNokkel = (r, k) => {
  if (!k || !k.er_bygg_F) return null;
  return `${k.kanonisk_sn2007} ${k.kanonisk_navn}`;
};
for (const [navn, rader] of Object.entries(KOH)) {
  out[`byggfag_${navn}`] = tabell(grupper(rader, byggNokkel), 1);
}

// ---- 2. Alle næringer (2-siffer) i hovedvinduet, for rangering ----
const naering2Navn = new Map();
for (const r of JSON.parse(readFileSync(`${DATA}/klass-SN2007-versjon30_${RUN_DATE}.json`, "utf8")).koder)
  if (String(r.niva) === "2") naering2Navn.set(r.kode, r.navn);

const n2 = (r, k) => {
  if (!k) return null;
  if (k.metode === "IKKE_NAERING") return "UOPPGITT";
  if (!k.kanonisk_sn2007) return "UTEN_KODE";
  const koder = [...new Set(k.kanonisk_sn2007.split("|").map((c) => c.slice(0, 2)))];
  return koder.length === 1 ? koder[0] : `FLERE:${koder.sort().join("+")}`;
};
out.naering2_hoved = tabell(grupper(KOH.hoved, n2), 1)
  .map((r) => ({ ...r, navn: naering2Navn.get(r.nokkel) ?? r.nokkel }))
  .sort((a, b) => b.n - a.n);

// ---- 3. De største enkeltnæringene (5-siffer), bygg + ikke-bygg ----
const n5 = (r, k) => {
  if (!k) return null;
  if (k.metode === "IKKE_NAERING") return "UOPPGITT (ingen næring oppgitt i kunngjøringen)";
  if (!k.kanonisk_sn2007) return null;
  return `${k.kanonisk_sn2007} ${k.kanonisk_navn}`;
};
const alle5 = tabell(grupper(KOH.hoved, n5), 1).sort((a, b) => b.n - a.n);
out.storste_naeringer_hoved = alle5.filter((r) => r.n >= 10).slice(0, 40);

// ---- 4. Underdekningen i den gamle kartmetoden ----
if (v1) {
  let byggV3 = 0, byggV1 = 0, kunV3 = new Map();
  for (const r of KOH.hoved) {
    const k = r.etikett ? kart.get(r.etikett.normalize("NFC")) : null;
    const erV3 = k?.er_bygg_F === true;
    const kodeV1 = r.etikett ? v1.get(r.etikett.normalize("NFC")) : null;
    const erV1 = /^4[123]/.test(kodeV1 || "");
    if (erV3) byggV3++;
    if (erV1) byggV1++;
    if (erV3 && !erV1) kunV3.set(r.etikett, (kunV3.get(r.etikett) ?? 0) + 1);
  }
  out.underdekning_gammelt_kart = {
    bygg_v3_klass: byggV3, bygg_v1_modal_selskapstekst: byggV1,
    tapt: byggV3 - byggV1,
    tapte_etiketter: [...kunV3.entries()].map(([e, n]) => ({ etikett: e, selskaper: n })).sort((a, b) => b.selskaper - a.selskaper),
  };
}

// ---- 5. Publiseringsuttrekk: n >= 10, ellers undertrykt ----
const publ = [];
for (const [navn, rader] of [["byggfag_moden", out.byggfag_moden], ["byggfag_hoved", out.byggfag_hoved]]) {
  let undertrykt_n = 0, undertrykt_grupper = 0;
  for (const r of rader) {
    if (r.n >= 10) publ.push([navn, r.nokkel, r.n, r.innstilt, r.avsluttet, r.apen,
      r.innstilt_pst.toFixed(1), r.ki95_lav_pst.toFixed(1), r.ki95_hoy_pst.toFixed(1), r.apen_pst.toFixed(1)]);
    else { undertrykt_n += r.n; undertrykt_grupper++; }
  }
  publ.push([navn, `UNDERTRYKT (n<10, ${undertrykt_grupper} grupper slått sammen)`, undertrykt_n, "", "", "", "", "", "", ""]);
}
const csv = writeCsv(`figurer/bransjetabell-bygg_${RUN_DATE}.csv`,
  ["sett", "naering", "n", "innstilt", "avsluttet", "fortsatt_apen",
   "innstilt_pst", "ki95_lav_pst", "ki95_hoy_pst", "apen_pst"], publ);
out.publiseringsuttrekk = csv;

writeJson(`data/bransjetabell-rapport_${RUN_DATE}.json`, out);

console.log(JSON.stringify({
  kjoredato: out.kjoredato,
  byggfag_moden: out.byggfag_moden.map((r) => `${r.nokkel} | n=${r.n} innstilt=${r.innstilt} ${r.innstilt_pst.toFixed(1)}% [${r.ki95_lav_pst.toFixed(1)}-${r.ki95_hoy_pst.toFixed(1)}] åpne=${r.apen_pst.toFixed(1)}%`),
  byggfag_hoved: out.byggfag_hoved.map((r) => `${r.nokkel} | n=${r.n} innstilt=${r.innstilt} ${r.innstilt_pst.toFixed(1)}% [${r.ki95_lav_pst.toFixed(1)}-${r.ki95_hoy_pst.toFixed(1)}]`),
  naering2_hoved: out.naering2_hoved.slice(0, 20).map((r) => `${r.nokkel} ${r.navn} | n=${r.n} ${r.innstilt_pst.toFixed(1)}% [${r.ki95_lav_pst.toFixed(1)}-${r.ki95_hoy_pst.toFixed(1)}]`),
  storste_naeringer: out.storste_naeringer_hoved.slice(0, 25).map((r) => `${r.nokkel} | n=${r.n} ${r.innstilt_pst.toFixed(1)}% [${r.ki95_lav_pst.toFixed(1)}-${r.ki95_hoy_pst.toFixed(1)}]`),
  underdekning: out.underdekning_gammelt_kart,
  csv,
}, null, 2));
await done();
