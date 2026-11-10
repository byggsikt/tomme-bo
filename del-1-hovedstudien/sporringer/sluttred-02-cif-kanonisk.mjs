// SLUTTREDAKSJON — regenerer figurgrunnlaget for figur 4 (READ-ONLY, kun SELECT).
//
// figurer/domstol-modningskurve-cif.tsv var beregnet paa den UTGAATTE byggavgrensningen
// (1 142 foretak, NACE-oppslag paa selskapstabellen) mens manusets figur 4 og tabellen i
// kapittel 8.1 siterer den kanoniske kurven (utforende bygg 1 280, etikett-kaskaden).
// En leser som reproduserte fra fila fikk 56,7/65,0 ved ett aar der teksten sier
// 57,2/65,2. Her regenereres fila med SAMME estimator (Aalen-Johansen, ukesgrid,
// samme filformat) paa den kanoniske definisjonen og den kanoniske utfallsregelen
// (forste utfallskunngjoring paa/etter aapningen; innstilling vinner ved samme dato).
// Skriptet asserterer mot talljournalens D3-ankere (50 % ved 267/205, 60 % ved 389/292).
import { getPool, closePool } from "./db.mjs";
import { writeFileSync } from "node:fs";
import { createHash } from "node:crypto";
import { slaaOpp, erByggUtforende } from "./kohort-bransjeklassifikator.mjs";

const ROOT = "./del-1-hovedstudien";
const KJORT = "2026-08-30";
const pool = getPool();

const SQL = `
with aapning as materialized (
  select orgnr, min(dato) as aapning
  from kunngjoring.insolvens where type = 'Konkurs - åpning' group by orgnr
),
kohort as materialized (
  select orgnr, aapning from aapning
  where aapning between date '2023-09-01' and date '2024-12-31'
),
attr as materialized (
  select i.orgnr, nullif(trim(i.bransje),'') as bransje
  from kunngjoring.insolvens i
  join kohort k on k.orgnr = i.orgnr and i.dato = k.aapning
  where i.type = 'Konkurs - åpning'
),
innst_etter as materialized (
  select i.orgnr, min(i.dato) as dato
  from kunngjoring.insolvens i join kohort k on k.orgnr = i.orgnr
  where i.type = 'Konkurs - innstilling av bobehandlingen' and i.dato >= k.aapning
  group by i.orgnr
),
avsl_etter as materialized (
  select i.orgnr, min(i.dato) as dato
  from kunngjoring.insolvens i join kohort k on k.orgnr = i.orgnr
  where i.type = 'Konkurs - avslutning av bobehandlingen' and i.dato >= k.aapning
  group by i.orgnr
)
select a.bransje,
       (ie.dato - k.aapning) as d_innst,
       (ae.dato - k.aapning) as d_avsl,
       (date '2026-08-24' - k.aapning) as d_sensur
from kohort k
left join attr a on a.orgnr = k.orgnr
left join innst_etter ie on ie.orgnr = k.orgnr
left join avsl_etter ae on ae.orgnr = k.orgnr
`;

try {
  await pool.query("set statement_timeout = '900s'");
  const rader = (await pool.query(SQL)).rows;
  if (rader.length !== 5165) throw new Error("kohorten er ikke 5165: " + rader.length);

  for (const r of rader) {
    r.bygg = erByggUtforende(slaaOpp(r.bransje).kode);
    if (r.d_innst !== null) { r.t = r.d_innst; r.arsak = 1; }        // innstilling (vinner ved samme dato)
    else if (r.d_avsl !== null) { r.t = r.d_avsl; r.arsak = 2; }     // avslutning = konkurrerende hendelse
    else { r.t = r.d_sensur; r.arsak = 0; }                          // sensurert ved korpusslutt
    if (r.t < 0) r.t = 0;
  }
  const bygg = rader.filter(r => r.bygg), ovrig = rader.filter(r => !r.bygg);
  console.log(`n=${rader.length} bygg=${bygg.length} øvrige=${ovrig.length}`);
  if (bygg.length !== 1280 || ovrig.length !== 3885) throw new Error("byggdefinisjonen er ikke kanonisk");

  // Aalen-Johansen — identisk numerikk med den opprinnelige figurfila
  function cif(rows) {
    const byT = new Map();
    for (const r of rows) {
      const e = byT.get(r.t) || { d1: 0, d2: 0, c: 0 };
      if (r.arsak === 1) e.d1++; else if (r.arsak === 2) e.d2++; else e.c++;
      byT.set(r.t, e);
    }
    const times = [...byT.keys()].sort((a, b) => a - b);
    let n = rows.length, S = 1, F = 0;
    const out = { times: [], cif: [] };
    for (const t of times) {
      const { d1, d2, c } = byT.get(t);
      F += S * (d1 / n);
      S *= 1 - (d1 + d2) / n;
      out.times.push(t); out.cif.push(F);
      n -= d1 + d2 + c;
      if (n <= 0) break;
    }
    return out;
  }
  const cifVed = (c, t) => { let v = 0; for (let i = 0; i < c.times.length; i++) { if (c.times[i] <= t) v = c.cif[i]; else break; } return v; };
  const cifTid = (c, p) => { for (let i = 0; i < c.times.length; i++) if (c.cif[i] >= p) return c.times[i]; return NaN; };

  const cB = cif(bygg), cO = cif(ovrig);
  const ankere = {
    tid50_bygg: cifTid(cB, 0.5), tid50_ovrige: cifTid(cO, 0.5),
    tid60_bygg: cifTid(cB, 0.6), tid60_ovrige: cifTid(cO, 0.6),
    ved365_bygg_pst: +(100 * cifVed(cB, 365)).toFixed(1),
    ved365_ovrige_pst: +(100 * cifVed(cO, 365)).toFixed(1),
  };
  console.log("ankere:", JSON.stringify(ankere));
  // talljournalen D3: 50 % ved 267/205, 60 % ved 389/292 (kanonisk definisjon)
  if (ankere.tid50_bygg !== 267 || ankere.tid50_ovrige !== 205 ||
      ankere.tid60_bygg !== 389 || ankere.tid60_ovrige !== 292)
    throw new Error("D3-ankerne reproduseres ikke — fila skrives ikke");

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
  const txt = `# Byggsikt — Tomme bo (domstol). Kjørt ${KJORT}. Sensureringsdato 2026-08-24.\n` +
    `# Kumulativ insidens (Aalen-Johansen) for INNSTILLING, med avslutning som\n` +
    `# konkurrerende hendelse. Kohort: konkursåpning 2023-09-01..2024-12-31 (n=5165).\n` +
    `# Bygg = utførende bygg og anlegg (SN2007 41.2+42+43, kanonisk definisjon, n=1280),\n` +
    `# næring lest av åpningskunngjøringens trykte etikett. Utfall = første\n` +
    `# utfallskunngjøring på/etter åpningen; ved samme dato vinner innstillingen.\n` +
    `# Datagrunnlag: offentlig tilgjengelige registerkunngjøringer om konkursbehandling.\n` +
    `# Kun aggregater. Ingen selskaper, personer eller bostyrere er identifisert.\n` +
    tsv(kurve, ["dager", "bygg", "ovrige", "i_risiko_bygg", "i_risiko_ovrige"]);
  writeFileSync(`${ROOT}/figurer/domstol-modningskurve-cif.tsv`, txt, "utf8");
  console.log(`skrev figurer/domstol-modningskurve-cif.tsv sha256=${createHash("sha256").update(txt, "utf8").digest("hex")}`);
} catch (e) {
  console.error("FEIL:", e.message);
  process.exitCode = 1;
} finally {
  await closePool();
}
