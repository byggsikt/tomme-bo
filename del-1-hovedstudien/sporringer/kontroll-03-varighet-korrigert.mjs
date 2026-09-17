// DATAKONTROLLØREN — varighet under KANONISK regel: utfall = første utfalls-
// kunngjøring PÅ/ETTER åpningsdatoen (jf. kontroll-02: 3 selskaper har i tillegg
// en eldre innstilling fra et tidligere, utgått konkursløp — de ER innstilt i dette).
// Bygg = utførende (41.2+42+43) via bransjekart-v3. READ-ONLY, kun aggregater.
import { getPool, closePool } from "./db.mjs";
import { readFileSync } from "node:fs";

const DATA = "./data";
const v3 = new Map(JSON.parse(readFileSync(`${DATA}/bransjekart-v3_2026-08-30.json`, "utf8"))
  .kart.map(r => [r.etikett, r]));
const pool = getPool();
const kv = (arr, q) => {
  if (!arr.length) return null;
  const s = arr.slice().sort((a, b) => a - b);
  const i = (s.length - 1) * q, lo = Math.floor(i), hi = Math.ceil(i);
  return lo === hi ? s[lo] : +(s[lo] + (s[hi] - s[lo]) * (i - lo)).toFixed(1);
};
function kmMedian(data) {
  const byT = new Map();
  for (const r of data) { const e = byT.get(r.t) || { d: 0, c: 0 }; r.event ? e.d++ : e.c++; byT.set(r.t, e); }
  let n = data.length, S = 1;
  for (const t of [...byT.keys()].sort((a, b) => a - b)) {
    const { d, c } = byT.get(t);
    if (d > 0) { S *= 1 - d / n; if (S <= 0.5) return t; }
    n -= d + c;
  }
  return null;
}
function cif(data) {
  const byT = new Map();
  for (const r of data) {
    const e = byT.get(r.t) || { d1: 0, d2: 0, c: 0 };
    if (r.arsak === 1) e.d1++; else if (r.arsak === 2) e.d2++; else e.c++;
    byT.set(r.t, e);
  }
  let n = data.length, S = 1, F = 0; const steg = [];
  for (const t of [...byT.keys()].sort((a, b) => a - b)) {
    const { d1, d2, c } = byT.get(t);
    F += S * d1 / n; S *= 1 - (d1 + d2) / n; steg.push([t, F]); n -= d1 + d2 + c;
    if (n <= 0) break;
  }
  return steg;
}
const cifVed = (st, t) => { let v = 0; for (const [tt, f] of st) { if (tt <= t) v = f; else break; } return v; };
const cifTid = (st, p) => { for (const [tt, f] of st) if (f >= p) return tt; return null; };

try {
  await pool.query("set statement_timeout = '600s'");
  const korpusslutt = (await pool.query(
    "select to_char(max(dato),'YYYY-MM-DD') d from kunngjoring.insolvens")).rows[0].d;
  const rader = (await pool.query(`
    with s as materialized (
      select orgnr, min(dato) filter (where type = 'Konkurs - åpning') as aapning
      from kunngjoring.insolvens group by orgnr
    ),
    koh as materialized (
      select orgnr, aapning from s
      where aapning between date '2023-09-01' and date '2024-12-31'
    ),
    utfall as materialized (
      select k.orgnr,
             min(i.dato) filter (where i.type = 'Konkurs - innstilling av bobehandlingen'
                                   and i.dato >= k.aapning) as innst,
             min(i.dato) filter (where i.type = 'Konkurs - avslutning av bobehandlingen'
                                   and i.dato >= k.aapning) as avsl
      from koh k join kunngjoring.insolvens i on i.orgnr = k.orgnr
      group by k.orgnr
    )
    select (u.innst - k.aapning) as d_innst, (u.avsl - k.aapning) as d_avsl,
           (date '${korpusslutt}' - k.aapning) as d_slutt,
           nullif(trim(i.bransje),'') as bransje
    from koh k
    left join utfall u on u.orgnr = k.orgnr
    join kunngjoring.insolvens i on i.orgnr = k.orgnr and i.dato = k.aapning
      and i.type = 'Konkurs - åpning'
  `)).rows;

  for (const r of rader) {
    const k = v3.get((r.bransje || "").split("\n")[0].trim());
    r.byggU = k ? k.er_bygg_kjerne === true : false;
  }
  const surv = (sett) => sett.map(r => r.d_innst !== null
    ? { t: r.d_innst, event: 1, arsak: 1 }
    : r.d_avsl !== null ? { t: r.d_avsl, event: 0, arsak: 2 }
    : { t: r.d_slutt, event: 0, arsak: 0 });
  const B = rader.filter(r => r.byggU), O = rader.filter(r => !r.byggU);
  const dB = B.filter(r => r.d_innst !== null).map(r => r.d_innst);
  const dO = O.filter(r => r.d_innst !== null).map(r => r.d_innst);
  const dA = rader.filter(r => r.d_innst !== null).map(r => r.d_innst);
  const sB = surv(B), sO = surv(O), cB = cif(sB), cO = cif(sO);
  console.log(JSON.stringify({
    kontroll: "varighet, kanonisk regel + v3 utforende-definisjon",
    n: rader.length, bygg: B.length, ovrige: O.length,
    innstilt: { alle: dA.length, bygg: dB.length, ovrige: dO.length },
    raa_median: { alle: kv(dA, 0.5), bygg: kv(dB, 0.5), ovrige: kv(dO, 0.5) },
    raa_kvartiler_bygg: [kv(dB, 0.25), kv(dB, 0.75)],
    raa_kvartiler_ovrige: [kv(dO, 0.25), kv(dO, 0.75)],
    km_median: { bygg: kmMedian(sB), ovrige: kmMedian(sO) },
    cif_tid_til_50pst: { bygg: cifTid(cB, 0.5), ovrige: cifTid(cO, 0.5) },
    cif_tid_til_60pst: { bygg: cifTid(cB, 0.6), ovrige: cifTid(cO, 0.6) },
    cif_ved_365: { bygg_pst: +(100 * cifVed(cB, 365)).toFixed(1), ovrige_pst: +(100 * cifVed(cO, 365)).toFixed(1) },
  }, null, 1));
} catch (e) { console.error("FEIL:", e.message); process.exitCode = 1; }
finally { await closePool(); }
