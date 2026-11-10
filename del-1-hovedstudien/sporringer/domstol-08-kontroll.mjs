// LANE 3 — domstol. Steg 8: konkurrerende risiko (Aalen-Johansen),
// permutasjonskontroll av den stratifiserte logrank-testen, og sensitivitet
// (utvidet byggdefinisjon, alternativ sensurering, brief-vinduet).
// READ-ONLY. Kjøres: node domstol-08-kontroll.mjs
import { writeFileSync, mkdirSync } from "node:fs";
import { createHash } from "node:crypto";
import { getPool, closePool } from "./db.mjs";
import { quantileSorted, kaplanMeier, kmQuantile, stratifiedLogrank } from "./domstol-stat.mjs";

const ROOT = "./del-1-hovedstudien";
const KJORT = new Date().toISOString().slice(0, 10);
mkdirSync(`${ROOT}/figurer`, { recursive: true });

const pool = getPool();
await pool.query("set statement_timeout = '900s'");

const KODE = (col) => `nullif(regexp_replace(
    coalesce(substring(upper(trim(${col})) from 'KON-+([A-Z0-9]+)'), ''),
    'KJENNELSE.*$', ''), '')`;

async function hentKohort(fra, til) {
  const SQL = `
  with aapning as materialized (
    select orgnr, min(dato) as aapning_dato from kunngjoring.insolvens
     where type = 'Konkurs - åpning' group by orgnr),
  kohort as materialized (
    select orgnr, aapning_dato from aapning
     where aapning_dato between date '${fra}' and date '${til}'),
  aap as materialized (
    select k.orgnr, k.aapning_dato,
           max(nullif(trim(i.tingrett),'')) as navn,
           max(${KODE("i.saksnr")})         as kode,
           max(nullif(trim(i.bransje),''))  as bransje
      from kohort k join kunngjoring.insolvens i
        on i.orgnr=k.orgnr and i.dato=k.aapning_dato and i.type='Konkurs - åpning'
     group by 1,2),
  innst as materialized (
    select k.orgnr, min(i.dato) as innst_dato from kohort k
      join kunngjoring.insolvens i on i.orgnr=k.orgnr
     where i.type='Konkurs - innstilling av bobehandlingen' group by 1),
  avsl as materialized (
    select k.orgnr, min(i.dato) as avsl_dato from kohort k
      join kunngjoring.insolvens i on i.orgnr=k.orgnr
     where i.type='Konkurs - avslutning av bobehandlingen' group by 1),
  nace as materialized (
    select trim(t) as tekst, min(trim(k)) as kode from (
      select industry_text_1 t, industry_code_1 k from company_intel.company
      union all select industry_text_2, industry_code_2 from company_intel.company
      union all select industry_text_3, industry_code_3 from company_intel.company) s
     where nullif(trim(t),'') is not null and nullif(trim(k),'') is not null group by 1),
  brmap as materialized (
    select a.bransje,
           min(n.kode) filter (where n.tekst = a.bransje) as nace_eksakt,
           min(n.kode) filter (where n.tekst like a.bransje || '%'
                                 or a.bransje like n.tekst || '%') as nace_prefiks
      from (select distinct bransje from aap where bransje is not null) a
      left join nace n on n.tekst = a.bransje or n.tekst like a.bransje || '%'
                                              or a.bransje like n.tekst || '%'
     group by 1)
  select a.navn, a.kode, b.nace_eksakt,
         coalesce(b.nace_eksakt,b.nace_prefiks) as nace_utvidet,
         to_char(a.aapning_dato,'YYYY-MM-DD') as aapning,
         to_char(i.innst_dato,'YYYY-MM-DD')   as innstilling,
         to_char(v.avsl_dato,'YYYY-MM-DD')    as avslutning
    from aap a left join brmap b on b.bransje=a.bransje
      left join innst i on i.orgnr=a.orgnr left join avsl v on v.orgnr=a.orgnr`;
  const { rows } = await pool.query(SQL);
  return rows;
}

const { rows: [{ korpusslutt }] } = await pool.query(
  `select to_char(max(dato),'YYYY-MM-DD') as korpusslutt from kunngjoring.insolvens`);
const DAY = 86400000, d = (s) => (s ? Date.parse(s + "T00:00:00Z") : null), slutt = d(korpusslutt);

function beredt(rows, { byggFelt = "nace_eksakt", avslSomSensur = true } = {}) {
  for (const r of rows) {
    r.bygg = /^(41|42|43)/.test(r[byggFelt] || "");
    r.t_aap = d(r.aapning); r.t_inn = d(r.innstilling); r.t_avs = d(r.avslutning);
    if (r.t_inn) { r.t = Math.round((r.t_inn - r.t_aap) / DAY); r.event = 1; r.arsak = 1; }
    else if (r.t_avs) {
      r.t = Math.round((r.t_avs - r.t_aap) / DAY);
      r.event = avslSomSensur ? 0 : 0; r.arsak = 2;
    } else { r.t = Math.round((slutt - r.t_aap) / DAY); r.event = 0; r.arsak = 0; }
    if (!avslSomSensur && r.arsak === 2) r.t = Math.round((slutt - r.t_aap) / DAY);
    if (r.t < 0) r.t = 0;
  }
  return rows;
}

/** Aalen-Johansen: kumulativ insidens for innstilling med avslutning som
 *  konkurrerende hendelse. arsak: 1=innstilling, 2=avslutning, 0=sensurert. */
function cif(rows) {
  const byT = new Map();
  for (const r of rows) {
    const e = byT.get(r.t) || { d1: 0, d2: 0, c: 0 };
    if (r.arsak === 1) e.d1++; else if (r.arsak === 2) e.d2++; else e.c++;
    byT.set(r.t, e);
  }
  const times = [...byT.keys()].sort((a, b) => a - b);
  let n = rows.length, S = 1, F = 0;
  const out = { times: [], cif: [], surv: [], atRisk: [] };
  for (const t of times) {
    const { d1, d2, c } = byT.get(t);
    F += S * (d1 / n);
    S *= 1 - (d1 + d2) / n;
    out.times.push(t); out.cif.push(F); out.surv.push(S); out.atRisk.push(n);
    n -= d1 + d2 + c;
    if (n <= 0) break;
  }
  return out;
}
const cifVed = (c, t) => { let v = 0; for (let i = 0; i < c.times.length; i++) { if (c.times[i] <= t) v = c.cif[i]; else break; } return v; };
const cifTid = (c, p) => { for (let i = 0; i < c.times.length; i++) if (c.cif[i] >= p) return c.times[i]; return NaN; };

const strataAv = (rows) => {
  const m = new Map();
  for (const r of rows) {
    const k = r.kode || `NAVN:${r.navn}`;
    if (!m.has(k)) m.set(k, { a: [], b: [] });
    (r.bygg ? m.get(k).a : m.get(k).b).push({ t: r.t, event: r.event });
  }
  return m;
};

// ================= HOVEDKOHORT =================
console.log("Henter hovedkohorten 2023-09-01..2024-12-31 …");
const base = beredt(await hentKohort("2023-09-01", "2024-12-31"));
const bygg = base.filter((r) => r.bygg), ovrig = base.filter((r) => !r.bygg);
console.log(`  n=${base.length}  bygg=${bygg.length}  øvrige=${ovrig.length}  sensureringsdato=${korpusslutt}`);

const cB = cif(bygg), cO = cif(ovrig);
console.log("\nKONKURRERENDE RISIKO (Aalen-Johansen), andel innstilt ved:");
for (const t of [180, 365, 547, 730]) {
  console.log(`  ${String(t).padStart(4)} dager:  bygg ${(100 * cifVed(cB, t)).toFixed(1)} %   øvrige ${(100 * cifVed(cO, t)).toFixed(1)} %`);
}
console.log(`  tid til 50 % innstilt: bygg ${cifTid(cB, 0.5)} dager, øvrige ${cifTid(cO, 0.5)} dager`);
console.log(`  tid til 60 % innstilt: bygg ${cifTid(cB, 0.6)} dager, øvrige ${cifTid(cO, 0.6)} dager`);

// ================= LOGRANK: ustratifisert vs stratifisert =================
const enStratum = new Map([["alle", {
  a: bygg.map((r) => ({ t: r.t, event: r.event })),
  b: ovrig.map((r) => ({ t: r.t, event: r.event })) }]]);
const lrU = stratifiedLogrank(enStratum);
const lrS = stratifiedLogrank(strataAv(base));
console.log(`\nLOGRANK  ustratifisert: z=${lrU.z.toFixed(3)} p=${lrU.p.toExponential(2)} HR=${lrU.hr.toFixed(3)}`);
console.log(`         stratifisert (23 kretser): z=${lrS.z.toFixed(3)} p=${lrS.p.toExponential(2)} HR=${lrS.hr.toFixed(3)}`);

// ================= PERMUTASJONSKONTROLL =================
// Stokk byggmerket INNENFOR hver krets. Da skal z ~ N(0,1) og p være uniform.
function permuter(rows, seed) {
  let s = seed >>> 0;
  const rnd = () => ((s = (s * 1664525 + 1013904223) >>> 0) / 4294967296);
  const perKrets = new Map();
  for (const r of rows) {
    const k = r.kode || `NAVN:${r.navn}`;
    if (!perKrets.has(k)) perKrets.set(k, []);
    perKrets.get(k).push(r);
  }
  const m = new Map();
  for (const [k, arr] of perKrets) {
    const nb = arr.filter((r) => r.bygg).length;
    const idx = arr.map((_, i) => i);
    for (let i = idx.length - 1; i > 0; i--) { const j = Math.floor(rnd() * (i + 1)); [idx[i], idx[j]] = [idx[j], idx[i]]; }
    const a = [], b = [];
    idx.forEach((ix, pos) => (pos < nb ? a : b).push({ t: arr[ix].t, event: arr[ix].event }));
    m.set(k, { a, b });
  }
  return m;
}
const zs = [];
for (let i = 0; i < 300; i++) zs.push(stratifiedLogrank(permuter(base, 12345 + i)).z);
zs.sort((a, b) => a - b);
const mean = zs.reduce((x, y) => x + y, 0) / zs.length;
const sd = Math.sqrt(zs.reduce((x, y) => x + (y - mean) ** 2, 0) / (zs.length - 1));
const ekstremere = zs.filter((z) => Math.abs(z) >= Math.abs(lrS.z)).length;
console.log(`\nPERMUTASJON (300 stokkinger innen krets): z-snitt=${mean.toFixed(3)} sd=${sd.toFixed(3)}` +
  `  min=${zs[0].toFixed(2)} maks=${zs[zs.length-1].toFixed(2)}`);
console.log(`  antall permutasjoner minst like ekstreme som observert (|z|=${Math.abs(lrS.z).toFixed(2)}): ${ekstremere}/300`);

// ================= SENSITIVITET =================
console.log("\nSENSITIVITET");
const utvidet = beredt(await hentKohort("2023-09-01", "2024-12-31"), { byggFelt: "nace_utvidet" });
const lrUtv = stratifiedLogrank(strataAv(utvidet));
console.log(`  utvidet byggdefinisjon (n_bygg=${utvidet.filter(r=>r.bygg).length}):` +
  ` z=${lrUtv.z.toFixed(3)} p=${lrUtv.p.toExponential(2)} HR=${lrUtv.hr.toFixed(3)}`);

const altSensur = beredt(await hentKohort("2023-09-01", "2024-12-31"), { avslSomSensur: false });
const lrAlt = stratifiedLogrank(strataAv(altSensur));
console.log(`  avslutning sensurert ved korpusslutt i stedet: z=${lrAlt.z.toFixed(3)} p=${lrAlt.p.toExponential(2)} HR=${lrAlt.hr.toFixed(3)}`);

const briefVindu = beredt(await hentKohort("2023-09-01", "2025-06-30"));
const bB = briefVindu.filter((r) => r.bygg), bO = briefVindu.filter((r) => !r.bygg);
const med = (a) => quantileSorted(a.filter((r) => r.innstilling).map((r) => Math.round((d(r.innstilling)-d(r.aapning))/DAY)).sort((x,y)=>x-y), 0.5);
const lrBrief = stratifiedLogrank(strataAv(briefVindu));
console.log(`  briefens vindu 2023-09-01..2025-06-30 (n=${briefVindu.length}): rå median bygg=${med(bB)} øvrige=${med(bO)}` +
  `  -> stratifisert z=${lrBrief.z.toFixed(3)} HR=${lrBrief.hr.toFixed(3)}`);

// KM-median per definisjon
const kmB = kaplanMeier(bygg.map(r=>({t:r.t,event:r.event}))), kmO = kaplanMeier(ovrig.map(r=>({t:r.t,event:r.event})));
console.log(`  KM-median bygg=${kmQuantile(kmB)} øvrige=${kmQuantile(kmO)} (årsaksspesifikk)`);

// ================= FIGURGRUNNLAG: CIF =================
const tsv = (rowsIn, cols) => [cols.join("\t"),
  ...rowsIn.map((r) => cols.map((c) => {
    const v = r[c];
    if (v === null || v === undefined || (typeof v === "number" && Number.isNaN(v))) return "";
    if (typeof v === "number" && !Number.isInteger(v)) return v.toFixed(6);
    return String(v);
  }).join("\t"))].join("\n") + "\n";

const kurve = [];
for (let t = 0; t <= 1090; t += 7) {
  kurve.push({ dager: t, bygg: cifVed(cB, t), ovrige: cifVed(cO, t),
    i_risiko_bygg: bygg.filter((r) => r.t >= t).length,
    i_risiko_ovrige: ovrig.filter((r) => r.t >= t).length });
}
const txt = `# Byggsikt — Tomme bo, lane 3. Kjørt ${KJORT}. Sensureringsdato ${korpusslutt}.\n` +
  `# Kumulativ insidens (Aalen-Johansen) for INNSTILLING, med avslutning som\n` +
  `# konkurrerende hendelse. Kohort: konkursåpning 2023-09-01..2024-12-31.\n` +
  `# Dette er modningskurven: andelen innstilt som funksjon av tid siden åpning.\n` +
  tsv(kurve, ["dager", "bygg", "ovrige", "i_risiko_bygg", "i_risiko_ovrige"]);
writeFileSync(`${ROOT}/figurer/domstol-modningskurve-cif.tsv`, txt, "utf8");
console.log(`\n  skrev figurer/domstol-modningskurve-cif.tsv  sha256=${createHash("sha256").update(txt,"utf8").digest("hex")}`);

await closePool();
