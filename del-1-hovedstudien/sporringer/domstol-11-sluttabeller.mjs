// LANE 3 — domstol. Steg 11: sluttabeller for publisering.
//  - per rettskrets (n>=100): utfall, Clopper-Pearson + Wilson, median/kvartiler,
//    KM-median, byggandel, OG en næringsmiks-standardisert forventning (indirekte
//    standardisering) slik at spennet ikke leses som domstolsprestasjon.
//  - modningstabell per åpningskvartal (høyresensureringsbeviset).
//  - ankerregister som JSON til metodegrunnlaget.
// READ-ONLY. Kjøres: node domstol-11-sluttabeller.mjs
import { writeFileSync, mkdirSync } from "node:fs";
import { createHash } from "node:crypto";
import { getPool, closePool } from "./db.mjs";
import { clopperPearson, wilson, quantileSorted, kaplanMeier, kmQuantile } from "./domstol-stat.mjs";

const ROOT = "./del-1-hovedstudien";
const KJORT = new Date().toISOString().slice(0, 10);
mkdirSync(`${ROOT}/data`, { recursive: true });
mkdirSync(`${ROOT}/figurer`, { recursive: true });

const pool = getPool();
await pool.query("set statement_timeout = '900s'");
const KODE = (c) => `nullif(regexp_replace(coalesce(substring(upper(trim(${c})) from 'KON-+([A-Z0-9]+)'),''),'KJENNELSE.*$',''),'')`;

const { rows: [{ korpusslutt }] } = await pool.query(
  `select to_char(max(dato),'YYYY-MM-DD') as korpusslutt from kunngjoring.insolvens`);

const { rows } = await pool.query(`
with aapning as materialized (
  select orgnr, min(dato) as aapning_dato from kunngjoring.insolvens
   where type='Konkurs - åpning' group by orgnr),
kohort as materialized (
  select orgnr, aapning_dato from aapning
   where aapning_dato between date '2023-09-01' and date '2024-12-31'),
aap as materialized (
  select k.orgnr, k.aapning_dato,
         max(nullif(trim(i.tingrett),'')) as navn, max(${KODE("i.saksnr")}) as kode,
         max(nullif(trim(i.bransje),'')) as bransje
    from kohort k join kunngjoring.insolvens i
      on i.orgnr=k.orgnr and i.dato=k.aapning_dato and i.type='Konkurs - åpning' group by 1,2),
innst as materialized (
  select k.orgnr, min(i.dato) as dt from kohort k join kunngjoring.insolvens i on i.orgnr=k.orgnr
   where i.type='Konkurs - innstilling av bobehandlingen' group by 1),
avsl as materialized (
  select k.orgnr, min(i.dato) as dt from kohort k join kunngjoring.insolvens i on i.orgnr=k.orgnr
   where i.type='Konkurs - avslutning av bobehandlingen' group by 1),
nace as materialized (
  select trim(t) as tekst, min(trim(k)) as kode from (
    select industry_text_1 t, industry_code_1 k from company_intel.company
    union all select industry_text_2, industry_code_2 from company_intel.company
    union all select industry_text_3, industry_code_3 from company_intel.company) s
   where nullif(trim(t),'') is not null and nullif(trim(k),'') is not null group by 1),
brmap as materialized (
  select a.bransje, min(n.kode) filter (where n.tekst = a.bransje) as nace_eksakt
    from (select distinct bransje from aap where bransje is not null) a
    left join nace n on n.tekst = a.bransje group by 1)
select a.navn, a.kode, b.nace_eksakt,
       to_char(a.aapning_dato,'YYYY-MM-DD') as aapning,
       to_char(date_trunc('quarter', a.aapning_dato),'YYYY-"K"Q') as kvartal,
       to_char(i.dt,'YYYY-MM-DD') as innstilling, to_char(v.dt,'YYYY-MM-DD') as avslutning
  from aap a left join brmap b on b.bransje=a.bransje
    left join innst i on i.orgnr=a.orgnr left join avsl v on v.orgnr=a.orgnr`);

const DAY = 86400000, d = (s) => (s ? Date.parse(s + "T00:00:00Z") : null), slutt = d(korpusslutt);
for (const r of rows) {
  r.bygg = /^(41|42|43)/.test(r.nace_eksakt || "");
  r.n2 = r.nace_eksakt ? r.nace_eksakt.slice(0, 2) : "ukjent";
  r.dager = r.innstilling ? Math.round((d(r.innstilling) - d(r.aapning)) / DAY) : null;
  if (r.innstilling) { r.t = r.dager; r.event = 1; }
  else if (r.avslutning) { r.t = Math.round((d(r.avslutning) - d(r.aapning)) / DAY); r.event = 0; }
  else { r.t = Math.round((slutt - d(r.aapning)) / DAY); r.event = 0; }
  if (r.t < 0) r.t = 0;
}

// nasjonal innstillingsrate per næringsbøtte (til indirekte standardisering)
const rate = new Map();
for (const r of rows) {
  const e = rate.get(r.n2) || { n: 0, k: 0 };
  e.n++; if (r.innstilling) e.k++;
  rate.set(r.n2, e);
}

const kretser = new Map();
for (const r of rows) {
  const k = r.kode || `NAVN:${r.navn}`;
  if (!kretser.has(k)) kretser.set(k, { kode: r.kode, navn: r.navn, s: [] });
  kretser.get(k).s.push(r);
}

const tab = [];
for (const [, k] of kretser) {
  const s = k.s, n = s.length;
  const inn = s.filter((r) => r.innstilling);
  const dager = inn.map((r) => r.dager).sort((a, b) => a - b);
  const [clo, chi] = clopperPearson(inn.length, n);
  const [wlo, whi] = wilson(inn.length, n);
  const forventet = s.reduce((acc, r) => { const e = rate.get(r.n2); return acc + e.k / e.n; }, 0);
  tab.push({
    rettskrets: k.navn, domstolskode: k.kode, saker: n,
    innstilt: inn.length, avsluttet: s.filter((r) => r.avslutning).length,
    fortsatt_apne: s.filter((r) => !r.innstilling && !r.avslutning).length,
    andel_innstilt: inn.length / n, cp95_lav: clo, cp95_hoy: chi,
    wilson95_lav: wlo, wilson95_hoy: whi,
    dager_q1: quantileSorted(dager, 0.25), dager_median: quantileSorted(dager, 0.5),
    dager_q3: quantileSorted(dager, 0.75),
    km_median_dager: kmQuantile(kaplanMeier(s.map((r) => ({ t: r.t, event: r.event })))),
    byggandel: s.filter((r) => r.bygg).length / n,
    forventet_andel_naeringsmiks: forventet / n,
    observert_delt_paa_forventet: inn.length / forventet,
    publiserbar_n100: n >= 100,
  });
}
tab.sort((a, b) => a.andel_innstilt - b.andel_innstilt);

const pub = tab.filter((r) => r.publiserbar_n100);
console.log(`Publiserbare kretser (n>=100): ${pub.length} av ${tab.length}, ` +
  `${pub.reduce((s, r) => s + r.saker, 0)} av ${rows.length} saker ` +
  `(${(100 * pub.reduce((s, r) => s + r.saker, 0) / rows.length).toFixed(1)} %)`);
console.log(`Spenn innstillingsandel: ${(100*pub[0].andel_innstilt).toFixed(1)} % (${pub[0].rettskrets})` +
  ` – ${(100*pub[pub.length-1].andel_innstilt).toFixed(1)} % (${pub[pub.length-1].rettskrets})`);
const medSort = pub.slice().sort((a, b) => a.dager_median - b.dager_median);
console.log(`Spenn median dager: ${medSort[0].dager_median} (${medSort[0].rettskrets})` +
  ` – ${medSort[medSort.length-1].dager_median} (${medSort[medSort.length-1].rettskrets})`);
const kmSort = pub.slice().sort((a, b) => a.km_median_dager - b.km_median_dager);
console.log(`Spenn KM-median: ${kmSort[0].km_median_dager} (${kmSort[0].rettskrets})` +
  ` – ${kmSort[kmSort.length-1].km_median_dager} (${kmSort[kmSort.length-1].rettskrets})`);
const oeSort = pub.slice().sort((a, b) => a.observert_delt_paa_forventet - b.observert_delt_paa_forventet);
console.log(`Spenn observert/forventet (næringsmiks-justert): ${oeSort[0].observert_delt_paa_forventet.toFixed(3)}` +
  ` (${oeSort[0].rettskrets}) – ${oeSort[oeSort.length-1].observert_delt_paa_forventet.toFixed(3)} (${oeSort[oeSort.length-1].rettskrets})`);
console.log(`Byggandel per krets: ${(100*Math.min(...pub.map(r=>r.byggandel))).toFixed(1)} – ` +
  `${(100*Math.max(...pub.map(r=>r.byggandel))).toFixed(1)} %`);
console.table(pub.map((r) => ({ rettskrets: r.rettskrets, saker: r.saker,
  andel: (100*r.andel_innstilt).toFixed(1), cp: `${(100*r.cp95_lav).toFixed(1)}–${(100*r.cp95_hoy).toFixed(1)}`,
  q1: r.dager_q1, median: r.dager_median, q3: r.dager_q3, km: r.km_median_dager,
  bygg_pst: (100*r.byggandel).toFixed(1), o_e: r.observert_delt_paa_forventet.toFixed(3) })));

// modningstabell
const kvartaler = new Map();
for (const r of rows) {
  const e = kvartaler.get(r.kvartal) || { n: 0, k: 0 };
  e.n++; if (r.innstilling) e.k++;
  kvartaler.set(r.kvartal, e);
}
const modning = [...kvartaler.entries()].sort().map(([kv, e]) => {
  const [lo, hi] = clopperPearson(e.k, e.n);
  return { kvartal: kv, saker: e.n, innstilt: e.k, andel: e.k / e.n, cp95_lav: lo, cp95_hoy: hi,
           mnd_oppfolging_min: Math.round((slutt - d(kv.replace(/(\d{4})-K(\d)/, (m, y, q) =>
             `${y}-${String(1 + (q - 1) * 3).padStart(2, "0")}-01`))) / DAY / 30.44) };
});
console.log("\nModning per åpningskvartal (kohortvinduet):");
console.table(modning.map((m) => ({ kvartal: m.kvartal, saker: m.saker, innstilt: m.innstilt,
  andel: (100 * m.andel).toFixed(1), ci: `${(100*m.cp95_lav).toFixed(1)}–${(100*m.cp95_hoy).toFixed(1)}` })));

// ---- skriv ----
const tsv = (rs, cols) => [cols.join("\t"), ...rs.map((r) => cols.map((c) => {
  const v = r[c];
  if (v === null || v === undefined || (typeof v === "number" && Number.isNaN(v))) return "";
  if (typeof v === "number" && !Number.isInteger(v)) return v.toFixed(6);
  return String(v);
}).join("\t"))].join("\n") + "\n";

const skriv = (rel, t) => { writeFileSync(`${ROOT}/${rel}`, t, "utf8");
  console.log(`  skrev ${rel}  sha256=${createHash("sha256").update(t, "utf8").digest("hex")}`); };

const HEAD = `# Byggsikt — «Tomme bo», lane 3 (domstol). Kjørt ${KJORT}. Datagrunnlag: offentlig
# tilgjengelige registerkunngjøringer om konkursbehandling. Sensureringsdato ${korpusslutt}.
# Kohort: alle selskaper med kunngjort konkursåpning der første åpning falt i
# 2023-09-01..2024-12-31 (n=${rows.length}). Rettskrets og næring leses av åpningskunngjøringen.
# Kun aggregater. Ingen selskaper, personer eller bostyrere er identifisert.
`;

console.log("\nFiler:");
skriv("data/domstol-sluttabell.tsv", HEAD +
`# andel_innstilt = andel av kretsens bo som er kunngjort innstilt (kkl. § 135).
# cp95_* = Clopper-Pearson 95 %, wilson95_* = Wilson score 95 %.
# dager_* = åpning->innstilling, KUN fullførte saker (nedoverbiasert ved sensurering).
# km_median_dager = Kaplan-Meier-median, håndterer at 6,8 % av boene ennå ikke er avgjort.
# forventet_andel_naeringsmiks = kretsens forventede andel hvis hver næring hadde
#   landsraten (indirekte standardisering); observert_delt_paa_forventet er nøkkeltallet.
# DESKRIPTIV VARIASJON. Sakstype (oppbud vs kreditorbegjæring) er IKKE observerbar i
# materialet, så tabellen kan ikke leses som en rangering av domstolenes innsats.
#
# MINSTECELLE: dette er en ARBEIDSFIL. Kolonnen fortsatt_apne er under 10 for
# TELEMARK TINGRETT (8) og NORD-TROMS OG SENJA TINGRETT (5), og flere av kretsene
# under n=100 har små celler. Publiseres tabellen må celler under 10 undertrykkes,
# eller bare kolonnene saker/innstilt/andel med intervall tas med (som i
# figurer/domstol-punktdiagram.tsv, som allerede er ren).
` + tsv(tab, ["rettskrets", "domstolskode", "saker", "innstilt", "avsluttet", "fortsatt_apne",
  "andel_innstilt", "cp95_lav", "cp95_hoy", "wilson95_lav", "wilson95_hoy",
  "dager_q1", "dager_median", "dager_q3", "km_median_dager", "byggandel",
  "forventet_andel_naeringsmiks", "observert_delt_paa_forventet", "publiserbar_n100"]));

skriv("figurer/domstol-punktdiagram.tsv", HEAD +
`# Figur: x = median dager åpning->innstilling, y = andel innstilt, boble = saker.
# Kun rettskretser med n>=100. Bruk km_median_dager for den sensureringsriktige varianten.
` + tsv(pub, ["rettskrets", "saker", "andel_innstilt", "cp95_lav", "cp95_hoy",
  "dager_median", "km_median_dager", "byggandel", "observert_delt_paa_forventet"]));

skriv("figurer/domstol-modningstabell.tsv", HEAD +
`# Andel innstilt per åpningskvartal. Platået 2023K3-2024K4 er beviset for at
# kohortvinduet er modent; fall etter 2024K4 er høyresensurering, ikke en trend.
` + tsv(modning, ["kvartal", "saker", "innstilt", "andel", "cp95_lav", "cp95_hoy", "mnd_oppfolging_min"]));

await closePool();
