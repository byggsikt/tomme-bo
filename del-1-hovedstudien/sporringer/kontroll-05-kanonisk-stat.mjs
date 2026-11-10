// DATAKONTROLLØREN — kanoniske teststørrelser (utfall = første utfall PÅ/ETTER åpning):
// khikvadrat bygg-vs-øvrige (begge parvarianter), stratifisert mediandifferanse,
// og strata-fortegn. READ-ONLY, kun aggregater.
import { getPool, closePool } from "./db.mjs";
import { readFileSync } from "node:fs";

const DATA = "./data";
const v3 = new Map(JSON.parse(readFileSync(`${DATA}/bransjekart-v3_2026-08-30.json`, "utf8"))
  .kart.map(r => [r.etikett, r]));
const kv = (arr, q) => {
  if (!arr.length) return null;
  const s = arr.slice().sort((a, b) => a - b);
  const i = (s.length - 1) * q, lo = Math.floor(i), hi = Math.ceil(i);
  return lo === hi ? s[lo] : s[lo] + (s[hi] - s[lo]) * (i - lo);
};
const chi2Yates = (a, b, c, d) => {
  const n = a + b + c + d;
  return n * Math.pow(Math.abs(a * d - b * c) - n / 2, 2) / ((a + b) * (c + d) * (a + c) * (b + d));
};
// p-verdi for chi2 df=1 (øvre hale) via komplementær feilfunksjon
const erfc = (x) => {
  const z = Math.abs(x), t = 1 / (1 + z / 2);
  const r = t * Math.exp(-z * z - 1.26551223 + t * (1.00002368 + t * (0.37409196 + t * (0.09678418 +
    t * (-0.18628806 + t * (0.27886807 + t * (-1.13520398 + t * (1.48851587 +
    t * (-0.82215223 + t * 0.17087277)))))))));
  return x >= 0 ? r : 2 - r;
};
const pChi1 = (x) => erfc(Math.sqrt(x / 2));

const pool = getPool();
try {
  await pool.query("set statement_timeout = '600s'");
  const rader = (await pool.query(`
    with s as materialized (
      select orgnr, min(dato) filter (where type = 'Konkurs - åpning') as aapning
      from kunngjoring.insolvens group by orgnr
    ),
    koh as materialized (
      select orgnr, aapning from s
      where aapning between date '2023-09-01' and date '2024-12-31'
    ),
    u as materialized (
      select k.orgnr,
             min(i.dato) filter (where i.type = 'Konkurs - innstilling av bobehandlingen'
                                   and i.dato >= k.aapning) as innst,
             min(i.dato) filter (where i.type = 'Konkurs - avslutning av bobehandlingen'
                                   and i.dato >= k.aapning) as avsl
      from koh k join kunngjoring.insolvens i on i.orgnr = k.orgnr group by k.orgnr
    )
    select (u.innst - k.aapning) as d_innst, (u.innst is not null) as i, (u.avsl is not null) as a,
           nullif(trim(o.bransje),'') as bransje, nullif(trim(o.tingrett),'') as tingrett
    from koh k
    left join u on u.orgnr = k.orgnr
    join kunngjoring.insolvens o on o.orgnr = k.orgnr and o.dato = k.aapning
      and o.type = 'Konkurs - åpning'
  `)).rows;
  for (const r of rader) {
    const k = v3.get((r.bransje || "").split("\n")[0].trim());
    r.byggU = k ? k.er_bygg_kjerne === true : false;
    r.byggF = k ? k.er_bygg_F === true : false;
    r.uoppgitt = k ? k.metode === "IKKE_NAERING" : false;
  }
  const bU = rader.filter(r => r.byggU), oU = rader.filter(r => !r.byggU);
  const bF = rader.filter(r => r.byggF), oX = rader.filter(r => !r.byggF && !r.uoppgitt);
  const c = (s) => s.filter(r => r.i).length;
  const x1 = chi2Yates(c(bU), bU.length - c(bU), c(oU), oU.length - c(oU));
  const x2 = chi2Yates(c(bF), bF.length - c(bF), c(oX), oX.length - c(oX));
  console.log(JSON.stringify({
    utforende_vs_komplement: { bygg: [c(bU), bU.length], ovrige: [c(oU), oU.length],
      diff_pp: +(100 * (c(bU) / bU.length - c(oU) / oU.length)).toFixed(2),
      chi2: +x1.toFixed(2), p: pChi1(x1).toExponential(2) },
    F_vs_ovrige_ekskl_uoppgitt: { bygg: [c(bF), bF.length], ovrige: [c(oX), oX.length],
      diff_pp: +(100 * (c(bF) / bF.length - c(oX) / oX.length)).toFixed(2),
      chi2: +x2.toFixed(2), p: pChi1(x2).toExponential(2) },
  }, null, 1));

  // stratifisert mediandifferanse, kanonisk regel
  const per = new Map();
  for (const r of rader) {
    const t = r.tingrett || "?";
    (per.get(t) || per.set(t, []).get(t)).push(r);
  }
  const strata = [];
  for (const [t, d] of per) {
    const bd = d.filter(r => r.byggU && r.d_innst !== null).map(r => r.d_innst);
    const od = d.filter(r => !r.byggU && r.d_innst !== null).map(r => r.d_innst);
    if (bd.length >= 10 && od.length >= 10)
      strata.push({ diff: kv(bd, 0.5) - kv(od, 0.5), vekt: bd.length + od.length });
  }
  const sv = strata.reduce((a, s) => a + s.vekt, 0);
  console.log(JSON.stringify({
    strata: strata.length, saker: sv,
    vektet_diff_dager: +(strata.reduce((a, s) => a + s.diff * s.vekt, 0) / sv).toFixed(1),
    bygg_tregere: strata.filter(s => s.diff > 0).length,
    bygg_raskere: strata.filter(s => s.diff < 0).length,
  }, null, 1));
} catch (e) { console.error("FEIL:", e.message); process.exitCode = 1; }
finally { await closePool(); }
