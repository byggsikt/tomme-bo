// LANE 3 — domstol. HOVEDANALYSE (READ-ONLY, kun SELECT).
//
// Produserer:
//   data/domstol-navnekart.tsv          navn -> krets/kode, alle vintager
//   data/domstol-kohort-per-krets.tsv   per rettskrets: n, utfall, andeler, CI, varighet
//   data/domstol-byggmiks.tsv           byggandel per krets
//   data/domstol-stratifisert-varighet.tsv  bygg vs øvrige, stratifisert på krets
//   figurer/domstol-punktdiagram.tsv    figurgrunnlag (andel vs median dager)
//   figurer/domstol-modningskurve.tsv   KM-kurver bygg vs øvrige
//
// Kohort: distinkte orgnr, type='Konkurs - åpning', GLOBAL min(dato) i
//         2023-09-01..2024-12-31 (L8/L14). Domstol og bransje leses fra
//         ÅPNINGSRADEN (bransje finnes ikke på utfallsrader).
// Kjøres: node domstol-07-hovedanalyse.mjs
import { writeFileSync, mkdirSync } from "node:fs";
import { createHash } from "node:crypto";
import { getPool, closePool } from "./db.mjs";
import { clopperPearson, wilson, quantileSorted, kaplanMeier, kmQuantile,
         stratifiedLogrank, standardisedKM } from "./domstol-stat.mjs";

const ROOT = "./del-1-hovedstudien";
const KJORT = new Date().toISOString().slice(0, 10);
mkdirSync(`${ROOT}/data`, { recursive: true });
mkdirSync(`${ROOT}/figurer`, { recursive: true });

const pool = getPool();
await pool.query("set statement_timeout = '900s'");

// Robust domstolskode: tåler 'kON', 'KON--' og den svelgede etiketten
// 'KON-THODKjennelse avsagt:' (parserdefekt, se funnene).
const KODE = (col) => `nullif(regexp_replace(
    coalesce(substring(upper(trim(${col})) from 'KON-+([A-Z0-9]+)'), ''),
    'KJENNELSE.*$', ''), '')`;

const NACE = `
nace as materialized (
  select trim(t) as tekst, min(trim(k)) as kode
    from (select industry_text_1 t, industry_code_1 k from company_intel.company
          union all select industry_text_2, industry_code_2 from company_intel.company
          union all select industry_text_3, industry_code_3 from company_intel.company) s
   where nullif(trim(t),'') is not null and nullif(trim(k),'') is not null
   group by 1)`;

const SQL = `
with aapning as materialized (
  select orgnr, min(dato) as aapning_dato
    from kunngjoring.insolvens where type = 'Konkurs - åpning' group by orgnr),
kohort as materialized (
  select orgnr, aapning_dato from aapning
   where aapning_dato between date '2023-09-01' and date '2024-12-31'),
aap as materialized (
  select k.orgnr, k.aapning_dato,
         max(nullif(trim(i.tingrett),''))          as navn,
         max(${KODE("i.saksnr")})                  as kode,
         max(nullif(trim(i.bransje),''))           as bransje
    from kohort k join kunngjoring.insolvens i
      on i.orgnr = k.orgnr and i.dato = k.aapning_dato and i.type = 'Konkurs - åpning'
   group by 1,2),
innst as materialized (
  select k.orgnr, min(i.dato) as innst_dato
    from kohort k join kunngjoring.insolvens i on i.orgnr = k.orgnr
   where i.type = 'Konkurs - innstilling av bobehandlingen' group by 1),
avsl as materialized (
  select k.orgnr, min(i.dato) as avsl_dato
    from kohort k join kunngjoring.insolvens i on i.orgnr = k.orgnr
   where i.type = 'Konkurs - avslutning av bobehandlingen' group by 1),
${NACE},
brmap as materialized (
  select a.bransje,
         min(n.kode) filter (where n.tekst = a.bransje)                as nace_eksakt,
         min(n.kode) filter (where n.tekst like a.bransje || '%'
                                or a.bransje like n.tekst || '%')      as nace_prefiks
    from (select distinct bransje from aap where bransje is not null) a
    left join nace n on n.tekst = a.bransje
                     or n.tekst like a.bransje || '%'
                     or a.bransje like n.tekst || '%'
   group by 1)
select a.navn, a.kode, a.bransje,
       b.nace_eksakt, coalesce(b.nace_eksakt, b.nace_prefiks) as nace_utvidet,
       to_char(a.aapning_dato,'YYYY-MM-DD') as aapning,
       to_char(i.innst_dato,'YYYY-MM-DD')   as innstilling,
       to_char(v.avsl_dato,'YYYY-MM-DD')    as avslutning
  from aap a
  left join brmap b on b.bransje = a.bransje
  left join innst i on i.orgnr = a.orgnr
  left join avsl  v on v.orgnr = a.orgnr`;

console.log("Henter kohorten …");
const t0 = Date.now();
const { rows } = await pool.query(SQL);
console.log(`  ${rows.length} saker på ${((Date.now() - t0) / 1000).toFixed(1)} s`);

// Korpusslutt = siste kunngjøringsdato i insolvens (sensureringsdato).
const { rows: [{ korpusslutt }] } = await pool.query(
  `select to_char(max(dato),'YYYY-MM-DD') as korpusslutt from kunngjoring.insolvens`);
console.log(`  korpusslutt (sensureringsdato) = ${korpusslutt}`);

// ---------- navnekart (alle vintager) ----------
const { rows: navnekart } = await pool.query(`
  select trim(tingrett) as navn, ${KODE("saksnr")} as kode,
         count(*) as rader, count(distinct orgnr) as selskaper,
         to_char(min(dato),'YYYY-MM-DD') as forste,
         to_char(max(dato),'YYYY-MM-DD') as siste
    from kunngjoring.insolvens
   where nullif(trim(tingrett),'') is not null
   group by 1,2 order by 1, min(dato)`);

// ---------- avledede felt ----------
const DAY = 86400000;
const d = (s) => (s ? Date.parse(s + "T00:00:00Z") : null);
const slutt = d(korpusslutt);

for (const r of rows) {
  r.bygg_streng   = /^(41|42|43)/.test(r.nace_eksakt  || "");
  r.bygg_utvidet  = /^(41|42|43)/.test(r.nace_utvidet || "");
  r.t_aap = d(r.aapning);
  r.t_inn = d(r.innstilling);
  r.t_avs = d(r.avslutning);
  r.dager_innst = r.t_inn ? Math.round((r.t_inn - r.t_aap) / DAY) : null;
  // tid-til-innstilling med sensurering: hendelse = innstilling; avslutning
  // uten innstilling er konkurrerende hendelse -> sensureres der (årsaks-
  // spesifikk hasard). Ellers sensureres saken ved korpusslutt.
  if (r.t_inn) { r.t = r.dager_innst; r.event = 1; }
  else if (r.t_avs) { r.t = Math.round((r.t_avs - r.t_aap) / DAY); r.event = 0; }
  else { r.t = Math.round((slutt - r.t_aap) / DAY); r.event = 0; }
  if (r.t < 0) r.t = 0;
}

// ---------- kontrolltall mot briefen ----------
const n = rows.length;
const innstilt = rows.filter((r) => r.innstilling).length;
const avsluttet = rows.filter((r) => r.avslutning).length;
const begge = rows.filter((r) => r.innstilling && r.avslutning).length;
const apen = rows.filter((r) => !r.innstilling && !r.avslutning).length;
const bygg = rows.filter((r) => r.bygg_streng);
const ovrig = rows.filter((r) => !r.bygg_streng);
console.log(`\nKONTROLL  n=${n}  innstilt=${innstilt} (${(100*innstilt/n).toFixed(1)}%)` +
  `  avsluttet=${avsluttet} (${(100*avsluttet/n).toFixed(1)}%)  åpne=${apen} (${(100*apen/n).toFixed(1)}%)  begge=${begge}`);
console.log(`  bygg(streng)=${bygg.length} innstilt=${bygg.filter(r=>r.innstilling).length}` +
  `  øvrige=${ovrig.length} innstilt=${ovrig.filter(r=>r.innstilling).length}`);
console.log(`  bygg(utvidet)=${rows.filter(r=>r.bygg_utvidet).length}`);

// ---------- per rettskrets ----------
const kretser = new Map();
for (const r of rows) {
  const key = r.kode || `NAVN:${r.navn}`;
  if (!kretser.has(key)) kretser.set(key, { kode: r.kode, navn: r.navn, saker: [] });
  kretser.get(key).saker.push(r);
}
const kretsrader = [];
for (const [, k] of kretser) {
  const s = k.saker, nn = s.length;
  const inn = s.filter((r) => r.innstilling);
  const dager = inn.map((r) => r.dager_innst).sort((a, b) => a - b);
  const [wlo, whi] = wilson(inn.length, nn);
  const [clo, chi] = clopperPearson(inn.length, nn);
  const km = kaplanMeier(s.map((r) => ({ t: r.t, event: r.event })));
  kretsrader.push({
    kode: k.kode, krets: k.navn, saker: nn,
    innstilt: inn.length,
    avsluttet: s.filter((r) => r.avslutning).length,
    apne: s.filter((r) => !r.innstilling && !r.avslutning).length,
    andel_innstilt: inn.length / nn,
    wilson_lav: wlo, wilson_hoy: whi, cp_lav: clo, cp_hoy: chi,
    dager_q1: quantileSorted(dager, 0.25),
    dager_median: quantileSorted(dager, 0.5),
    dager_q3: quantileSorted(dager, 0.75),
    km_median: kmQuantile(km, 0.5),
    bygg_streng: s.filter((r) => r.bygg_streng).length,
    byggandel: s.filter((r) => r.bygg_streng).length / nn,
    publiserbar: nn >= 100,
  });
}
kretsrader.sort((a, b) => b.saker - a.saker);

// ---------- stratifisert varighet: bygg vs øvrige ----------
const strata = new Map();
for (const [key, k] of kretser) {
  strata.set(key, {
    a: k.saker.filter((r) => r.bygg_streng).map((r) => ({ t: r.t, event: r.event })),
    b: k.saker.filter((r) => !r.bygg_streng).map((r) => ({ t: r.t, event: r.event })),
  });
}
const lr = stratifiedLogrank(strata);
const kmBygg = kaplanMeier(strata.size ? [...strata.values()].flatMap((g) => g.a) : []);
const kmOvrig = kaplanMeier([...strata.values()].flatMap((g) => g.b));
const stdOvrig = standardisedKM(strata, "a", "b");   // øvrige med byggs domstolsmiks
const stdBygg  = standardisedKM(strata, "b", "a");   // bygg med øvriges domstolsmiks

const medStd = (c) => { for (let i = 0; i < c.times.length; i++) if (c.surv[i] <= 0.5) return c.times[i]; return NaN; };

// rå medianer på fullførte saker (den formen briefen rapporterte)
const raaMed = (arr) => quantileSorted(arr.filter((r) => r.innstilling)
  .map((r) => r.dager_innst).sort((a, b) => a - b), 0.5);

console.log(`\nVARIGHET  rå median (fullførte saker): bygg=${raaMed(bygg)}  øvrige=${raaMed(ovrig)}`);
console.log(`  KM-median (sensurering håndtert): bygg=${kmQuantile(kmBygg)}  øvrige=${kmQuantile(kmOvrig)}`);
console.log(`  domstolsstandardisert KM-median: bygg=${medStd(stdBygg)} (øvriges miks), øvrige=${medStd(stdOvrig)} (byggs miks)`);
console.log(`  stratifisert logrank (krets som strata): O=${lr.O.toFixed(1)} E=${lr.E.toFixed(1)}` +
  ` V=${lr.V.toFixed(1)} z=${lr.z.toFixed(3)} p=${lr.p.toExponential(2)} HR(bygg vs øvrige)=${lr.hr.toFixed(3)}`);

// per krets: median bygg vs øvrige (fullførte saker)
const stratrader = [];
for (const [, k] of kretser) {
  const b = k.saker.filter((r) => r.bygg_streng && r.innstilling).map((r) => r.dager_innst).sort((x, y) => x - y);
  const o = k.saker.filter((r) => !r.bygg_streng && r.innstilling).map((r) => r.dager_innst).sort((x, y) => x - y);
  stratrader.push({
    kode: k.kode, krets: k.navn, saker: k.saker.length,
    bygg_innstilt: b.length, ovrig_innstilt: o.length,
    bygg_median: b.length ? quantileSorted(b, 0.5) : NaN,
    ovrig_median: o.length ? quantileSorted(o, 0.5) : NaN,
    diff: b.length && o.length ? quantileSorted(b, 0.5) - quantileSorted(o, 0.5) : NaN,
    publiserbar: k.saker.length >= 100,
  });
}
stratrader.sort((a, b) => b.saker - a.saker);
const vektet = stratrader.filter((r) => Number.isFinite(r.diff) && r.bygg_innstilt >= 5 && r.ovrig_innstilt >= 5);
const wSum = vektet.reduce((s, r) => s + r.bygg_innstilt, 0);
const diffVektet = vektet.reduce((s, r) => s + r.diff * r.bygg_innstilt, 0) / wSum;
console.log(`  byggvektet snitt av innen-krets medianforskjeller: ${diffVektet.toFixed(1)} dager` +
  ` (${vektet.length} kretser, ${wSum} byggsaker)`);

// ---------- skriv filer ----------
const tsv = (rowsIn, cols) => [cols.join("\t"),
  ...rowsIn.map((r) => cols.map((c) => {
    const v = r[c];
    if (v === null || v === undefined || (typeof v === "number" && Number.isNaN(v))) return "";
    if (typeof v === "number" && !Number.isInteger(v)) return v.toFixed(6);
    return String(v);
  }).join("\t"))].join("\n") + "\n";

const skriv = (rel, text) => {
  const p = `${ROOT}/${rel}`;
  writeFileSync(p, text, "utf8");
  const sha = createHash("sha256").update(text, "utf8").digest("hex");
  console.log(`  skrev ${rel}  sha256=${sha}`);
  return sha;
};

const head = `# Byggsikt — Tomme bo, lane 3 (domstol). Kjørt ${KJORT}. Sensureringsdato ${korpusslutt}.\n` +
  `# Kohort: distinkte orgnr, konkursåpning med global min(dato) i 2023-09-01..2024-12-31 (n=${n}).\n` +
  `# Domstol og bransje fra ÅPNINGSRADEN. Kun aggregater; ingen selskaper eller personer.\n`;

console.log("\nFiler:");
skriv("data/domstol-navnekart.tsv", head +
  `# Alle tingrettsnavn i kunngjoring.insolvens med domstolskode fra saksnr, alle vintager.\n` +
  tsv(navnekart, ["navn", "kode", "rader", "selskaper", "forste", "siste"]));

skriv("data/domstol-kohort-per-krets.tsv", head +
  `# Andeler med Wilson- og Clopper-Pearson-intervall (95 %). dager_* = åpning->innstilling,\n` +
  `# beregnet KUN på fullførte saker; km_median = Kaplan-Meier-median som håndterer sensurering.\n` +
  tsv(kretsrader, ["kode", "krets", "saker", "innstilt", "avsluttet", "apne", "andel_innstilt",
    "wilson_lav", "wilson_hoy", "cp_lav", "cp_hoy", "dager_q1", "dager_median", "dager_q3",
    "km_median", "bygg_streng", "byggandel", "publiserbar"]));

skriv("data/domstol-stratifisert-varighet.tsv", head +
  `# Innen-krets sammenlikning bygg vs øvrige, median dager åpning->innstilling.\n` +
  tsv(stratrader, ["kode", "krets", "saker", "bygg_innstilt", "ovrig_innstilt",
    "bygg_median", "ovrig_median", "diff", "publiserbar"]));

skriv("figurer/domstol-punktdiagram.tsv", head +
  `# Figur: x = median dager åpning->innstilling, y = andel innstilt, boble = saker.\n` +
  `# Kun kretser med n>=100 er publiserbare.\n` +
  tsv(kretsrader.filter((r) => r.publiserbar),
    ["krets", "saker", "andel_innstilt", "cp_lav", "cp_hoy", "dager_median", "byggandel"]));

const kurve = [];
const push = (navn, km) => km.times.forEach((t, i) =>
  kurve.push({ serie: navn, dager: t, andel_innstilt: 1 - km.surv[i], i_risiko: km.atRisk[i] }));
push("bygg", kmBygg); push("ovrige", kmOvrig);
stdOvrig.times.forEach((t, i) => kurve.push({ serie: "ovrige_std_byggmiks", dager: t, andel_innstilt: 1 - stdOvrig.surv[i], i_risiko: "" }));
skriv("figurer/domstol-modningskurve.tsv", head +
  `# Kaplan-Meier: andel innstilt som funksjon av dager siden åpning.\n` +
  `# ovrige_std_byggmiks = øvrige næringer standardisert til byggs domstolsmiks.\n` +
  tsv(kurve, ["serie", "dager", "andel_innstilt", "i_risiko"]));

skriv("data/domstol-byggmiks.tsv", head +
  `# Byggandel av porteføljen per rettskrets (streng definisjon).\n` +
  tsv(kretsrader.map((r) => ({ krets: r.krets, kode: r.kode, saker: r.saker,
    bygg: r.bygg_streng, byggandel: r.byggandel })), ["krets", "kode", "saker", "bygg", "byggandel"]));

await closePool();
