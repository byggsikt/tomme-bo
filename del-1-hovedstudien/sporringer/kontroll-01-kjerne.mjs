// DATAKONTROLLØREN — uavhengig reproduksjon av kjernetallene i «Tomme bo».
// READ-ONLY: kun SELECT (+ set statement_timeout på egen økt). Skrevet uavhengig av
// lanenes skript: én-pass FILTER-aggregering per orgnr i stedet for join-kaskadene.
//
// Regler fulgt: L8/L14 (count distinct orgnr, kohort = første åpning per selskap),
// L5 (nullif(trim())), L16 (livslop IKKE brukt), død-NACE (bransje fra åpningsraden),
// L17 (klassifisering via SSB Klass-kartene, begge vintager), personvern (ingen
// orgnr/saksnr forlater prosessen; alt som skrives er aggregater).
//
// Kjør: node kontroll-01-kjerne.mjs
import { getPool, closePool } from "./db.mjs";
import { readFileSync, writeFileSync } from "node:fs";
import { createHash } from "node:crypto";
import { slaaOpp, erByggF, erByggUtforende, IKKE_NAERING } from "./kohort-bransjeklassifikator.mjs";

const DATA = "./data";
const KJORT = new Date().toISOString().slice(0, 10);
const FRA = "2023-09-01", TIL = "2024-12-31";
const pool = getPool();
const res = {};
const out = (k, v) => { res[k] = v; console.log("\n=== " + k + " ==="); console.log(JSON.stringify(v, null, 1)); };
const pst = (a, b) => (b ? +(100 * a / b).toFixed(2) : null);

// v3-kartet (lane 2) som ANDRE klassifikator — kryssvalideres mot lane 1s klassifikator.
const v3 = new Map(JSON.parse(readFileSync(`${DATA}/bransjekart-v3_2026-08-30.json`, "utf8"))
  .kart.map(r => [r.etikett, r]));

function kvantil(arr, q) {
  if (!arr.length) return null;
  const s = arr.slice().sort((a, b) => a - b);
  const i = (s.length - 1) * q, lo = Math.floor(i), hi = Math.ceil(i);
  return lo === hi ? s[lo] : +(s[lo] + (s[hi] - s[lo]) * (i - lo)).toFixed(1);
}
// Kaplan-Meier (produkt-grense). data: [{t, event}] der event=1 er innstilling.
function kmMedian(data) {
  const byT = new Map();
  for (const r of data) {
    const e = byT.get(r.t) || { d: 0, c: 0 };
    r.event ? e.d++ : e.c++; byT.set(r.t, e);
  }
  let n = data.length, S = 1;
  for (const t of [...byT.keys()].sort((a, b) => a - b)) {
    const { d, c } = byT.get(t);
    if (d > 0) { S *= 1 - d / n; if (S <= 0.5) return t; }
    n -= d + c;
  }
  return null; // median ikke nådd
}
// Aalen-Johansen CIF for innstilling (arsak 1) med avslutning (2) som konkurrerende.
function cif(data) {
  const byT = new Map();
  for (const r of data) {
    const e = byT.get(r.t) || { d1: 0, d2: 0, c: 0 };
    if (r.arsak === 1) e.d1++; else if (r.arsak === 2) e.d2++; else e.c++;
    byT.set(r.t, e);
  }
  let n = data.length, S = 1, F = 0;
  const steg = [];
  for (const t of [...byT.keys()].sort((a, b) => a - b)) {
    const { d1, d2, c } = byT.get(t);
    F += S * d1 / n; S *= 1 - (d1 + d2) / n;
    steg.push([t, F]); n -= d1 + d2 + c;
    if (n <= 0) break;
  }
  return steg;
}
const cifVed = (steg, t) => { let v = 0; for (const [tt, f] of steg) { if (tt <= t) v = f; else break; } return v; };
const cifTid = (steg, p) => { for (const [tt, f] of steg) if (f >= p) return tt; return null; };
// khikvadrat 2x2 med Yates
function chi2Yates(a, b, c, d) {
  const n = a + b + c + d;
  const num = n * Math.pow(Math.abs(a * d - b * c) - n / 2, 2);
  const den = (a + b) * (c + d) * (a + c) * (b + d);
  return den ? num / den : null;
}
// Fisher eksakt toveis for 2x2 [[a,b],[c,d]]
function fisher2x2(a, b, c, d) {
  const lf = [0]; for (let i = 1; i <= a + b + c + d; i++) lf[i] = lf[i - 1] + Math.log(i);
  const lp = (x) => lf[a + b] + lf[c + d] + lf[a + c] + lf[b + d] - lf[a + b + c + d]
    - lf[x] - lf[a + b - x] - lf[a + c - x] - lf[c + d - (a + c - x)];
  const p0 = lp(a);
  let s = 0;
  const lo = Math.max(0, a + c - (c + d)), hi = Math.min(a + b, a + c);
  for (let x = lo; x <= hi; x++) if (lp(x) <= p0 + 1e-9) s += Math.exp(lp(x));
  return s;
}

try {
  await pool.query("set statement_timeout = '900s'");
  const korpusslutt = (await pool.query(
    "select to_char(max(dato),'YYYY-MM-DD') d from kunngjoring.insolvens")).rows[0].d;

  // ---------- 0 TYPE-SENSUS + seriestarter (som tekst, aldri JS-Date)
  const typer = (await pool.query(`
    select type, count(*) as rader, count(distinct orgnr) as selskaper,
           to_char(min(dato),'YYYY-MM-DD') as forste, to_char(max(dato),'YYYY-MM-DD') as siste
    from kunngjoring.insolvens
    where type ilike '%konkurs%' or type ilike '%bobehandling%'
    group by 1 order by 2 desc`)).rows;
  out("0_typer_og_seriestarter", { korpusslutt, typer });

  // ---------- 1 KOHORT: én-pass aggregering per orgnr (uavhengig form)
  const rader = (await pool.query(`
    with s as materialized (
      select orgnr,
             min(dato) filter (where type = 'Konkurs - åpning')                          as aapning,
             min(dato) filter (where type = 'Konkurs - innstilling av bobehandlingen')   as innst,
             min(dato) filter (where type = 'Konkurs - avslutning av bobehandlingen')    as avsl,
             min(dato) filter (where type = 'Fortsettelse av bobehandling')              as forts,
             min(dato) filter (where type = 'Sletting')                                  as slett
      from kunngjoring.insolvens group by orgnr
    ),
    koh as materialized (
      select * from s where aapning between date '${FRA}' and date '${TIL}'
    )
    select to_char(k.aapning,'YYYY-MM-DD') as aapning,
           to_char(k.innst,'YYYY-MM-DD')  as innst,
           to_char(k.avsl,'YYYY-MM-DD')   as avsl,
           to_char(k.forts,'YYYY-MM-DD')  as forts,
           (k.slett is not null)          as har_slettkunngj,
           coalesce(c.is_deleted, false)  as slettet_i_reg,
           nullif(trim(i.bransje),'')  as bransje,
           nullif(trim(i.tingrett),'') as tingrett,
           upper(nullif(trim(i.saksnr),'')) as saksnr,
           nullif(trim(i.bostyrer),'') is not null as har_bostyrer,
           nullif(trim(i.fristdag::text),'') is not null as har_fristdag,
           nullif(trim(i.kapital),'') is not null as har_kapital
    from koh k
    join kunngjoring.insolvens i on i.orgnr = k.orgnr and i.dato = k.aapning and i.type = 'Konkurs - åpning'
    left join company_intel.company c on c.orgnr = k.orgnr
  `)).rows;

  // fingeravtrykk beregnet I databasen — orgnr forlater aldri prosessen
  const fp = (await pool.query(`
    with s as materialized (
      select orgnr, min(dato) filter (where type='Konkurs - åpning') as aapning
      from kunngjoring.insolvens group by orgnr
    )
    select encode(sha256(convert_to(string_agg(orgnr, ',' order by orgnr),'UTF8')),'hex') as fp,
           count(*) as n
    from s where aapning between date '${FRA}' and date '${TIL}'`)).rows[0];

  const D = (s) => Date.parse(s + "T00:00:00Z");
  for (const r of rader) {
    r.i = !!r.innst && r.innst >= r.aapning;       // innstilling PÅ/ETTER åpning
    r.a = !!r.avsl && r.avsl >= r.aapning;
    r.innst_foer_aapning = !!r.innst && r.innst < r.aapning;
    r.avsl_foer_aapning = !!r.avsl && r.avsl < r.aapning;
    r.d_innst = r.i ? Math.round((D(r.innst) - D(r.aapning)) / 86400000) : null;
    r.oppf = Math.round((D(korpusslutt) - D(r.aapning)) / 86400000);
    // klassifikator 1 (lane 1, kaskade mot SSB Klass)
    const k1 = slaaOpp(r.bransje);
    r.nace1 = k1.kode;
    // klassifikator 2 (lane 2s v3-kart, flagg)
    const forste = (r.bransje || "").split("\n")[0].trim();
    const k2 = v3.get(forste) || v3.get(r.bransje || "") || null;
    r.byggF_1 = erByggF(r.nace1); r.byggU_1 = erByggUtforende(r.nace1);
    r.byggF_2 = k2 ? k2.er_bygg_F === true : false;
    r.byggU_2 = k2 ? k2.er_bygg_kjerne === true : false;
    r.uoppgitt = IKKE_NAERING.has(forste);
  }

  const n = rader.length;
  const innstAlle = rader.filter(r => r.i).length;
  const avslAlle = rader.filter(r => r.a).length;
  const begge = rader.filter(r => r.i && r.a).length;
  const apne = rader.filter(r => !r.i && !r.a).length;
  out("1_kohort_og_utfall", {
    kohort: n, fingeravtrykk: fp.fp, fingeravtrykk_n: Number(fp.n),
    innstilt: innstAlle, innstilt_pst_2des: pst(innstAlle, n),
    avsluttet_uansett: avslAlle, kun_avsluttet: avslAlle - begge, begge,
    fortsatt_apne: apne, apne_pst: pst(apne, n),
    sum_gjensidig_utelukkende: (innstAlle) + (avslAlle - begge) + apne,
    utfall_foer_aapning: rader.filter(r => r.innst_foer_aapning || r.avsl_foer_aapning).length,
    fortsettelse_av_bobehandling: rader.filter(r => r.forts).length,
    begge_med_fortsettelse: rader.filter(r => r.i && r.a && r.forts).length,
    oppfolging_dager: { min: Math.min(...rader.map(r => r.oppf)),
      min_mnd: +(Math.min(...rader.map(r => r.oppf)) / 30.44).toFixed(1),
      median: kvantil(rader.map(r => r.oppf), 0.5), maks: Math.max(...rader.map(r => r.oppf)) },
  });

  // ---------- 2 BYGG under BEGGE klassifikatorer (kryssvalidering utført av kontrolløren)
  const grp = (navn, sett) => {
    const i = sett.filter(r => r.i).length, a = sett.filter(r => r.a).length;
    const b = sett.filter(r => r.i && r.a).length, o = sett.filter(r => !r.i && !r.a).length;
    return { gruppe: navn, aapninger: sett.length, innstilt: i, innstilt_pst: pst(i, sett.length),
             avsluttet: a, begge: b, apne: o, apne_pst: pst(o, sett.length) };
  };
  const uenige = rader.filter(r => r.byggU_1 !== r.byggU_2 || r.byggF_1 !== r.byggF_2);
  out("2_bygg_begge_klassifikatorer", {
    klassifikator_uenighet_selskaper: uenige.length,
    uenige_etiketter: [...new Set(uenige.map(r => (r.bransje || "").split("\n")[0]))].slice(0, 12),
    k1_lane1_kaskade: [grp("BYGG utforende", rader.filter(r => r.byggU_1)),
                       grp("BYGG F 41-43", rader.filter(r => r.byggF_1)),
                       grp("eiendomsutvikling 41.1", rader.filter(r => r.byggF_1 && !r.byggU_1)),
                       grp("OVRIGE (komplement utforende)", rader.filter(r => !r.byggU_1)),
                       grp("OVRIGE ekskl F ekskl uoppgitt", rader.filter(r => !r.byggF_1 && !r.uoppgitt)),
                       grp("uoppgitt-bucket", rader.filter(r => r.uoppgitt)),
                       grp("uten kode (alle)", rader.filter(r => !r.nace1))],
    k2_lane2_v3kart: [grp("BYGG kjerne", rader.filter(r => r.byggU_2)),
                      grp("BYGG F 41-43", rader.filter(r => r.byggF_2))],
  });

  // signifikans bygg vs øvrige (to varianter)
  const bU = rader.filter(r => r.byggU_1), oU = rader.filter(r => !r.byggU_1);
  const bF = rader.filter(r => r.byggF_1), oX = rader.filter(r => !r.byggF_1 && !r.uoppgitt);
  const biU = bU.filter(r => r.i).length, oiU = oU.filter(r => r.i).length;
  const biF = bF.filter(r => r.i).length, oiX = oX.filter(r => r.i).length;
  out("2b_signifikans", {
    utforende_vs_komplement: { diff_pp: +(100 * (biU / bU.length - oiU / oU.length)).toFixed(2),
      chi2_yates: +chi2Yates(biU, bU.length - biU, oiU, oU.length - oiU).toFixed(2) },
    F_vs_ovrige_ekskl_uoppgitt: { diff_pp: +(100 * (biF / bF.length - oiX / oX.length)).toFixed(2),
      chi2_yates: +chi2Yates(biF, bF.length - biF, oiX, oX.length - oiX).toFixed(2) },
    apne_utforende_vs_komplement: { bygg_pst: pst(bU.filter(r => !r.i && !r.a).length, bU.length),
      ovrige_pst: pst(oU.filter(r => !r.i && !r.a).length, oU.length) },
  });

  // ---------- 3 BYGGFAG (forstelinje-match), kanonisk vindu + briefens vindu
  const fag = ["Snekkerarbeid", "Grunnarbeid", "Malerarbeid", "Elektrisk installasjonsarbeid",
               "Oppføring av bygninger", "Rørleggerarbeid", "Annen spesialisert bygge- og anleggsvirksomhet"];
  const fagTab = (sett) => fag.map(f => {
    const d = sett.filter(r => (r.bransje || "").split("\n")[0].trim() === f);
    const i = d.filter(r => r.i).length;
    return { fag: f, n: d.length, innstilt: i, pst: pst(i, d.length) };
  });
  out("3_byggfag_kanonisk_vindu", fagTab(rader));
  // briefens vindu 2023-08-24..2024-12-31 krever egen henting (kohorten er 09-01+)
  const brief = (await pool.query(`
    with s as materialized (
      select orgnr,
             min(dato) filter (where type = 'Konkurs - åpning') as aapning,
             min(dato) filter (where type = 'Konkurs - innstilling av bobehandlingen') as innst
      from kunngjoring.insolvens group by orgnr
    )
    select split_part(nullif(trim(i.bransje),''), e'\n', 1) as fag,
           count(*) as n, count(*) filter (where s.innst is not null) as innstilt
    from s join kunngjoring.insolvens i
      on i.orgnr = s.orgnr and i.dato = s.aapning and i.type = 'Konkurs - åpning'
    where s.aapning between date '2023-08-24' and date '2024-12-31'
      and split_part(nullif(trim(i.bransje),''), e'\n', 1) = any($1::text[])
    group by 1 order by 2 desc`, [fag.slice(0, 6)])).rows;
  out("3b_byggfag_briefens_vindu", brief);
  // Fisher: snekker vs rørlegger, moden kohort (138/178 vs 55/83)
  const sn = brief.find(r => r.fag === "Snekkerarbeid"), ro = brief.find(r => r.fag === "Rørleggerarbeid");
  out("3c_fisher_snekker_vs_rorlegger", {
    p_toveis: +fisher2x2(Number(sn.innstilt), Number(sn.n) - Number(sn.innstilt),
                         Number(ro.innstilt), Number(ro.n) - Number(ro.innstilt)).toFixed(4) });

  // ---------- 4 VARIGHET: rå + KM + CIF (utforende-definisjonen)
  const dg = (sett) => sett.filter(r => r.d_innst !== null).map(r => r.d_innst);
  out("4_varighet_raa", {
    alle: { n: dg(rader).length, median: kvantil(dg(rader), 0.5) },
    bygg_utf: { n: dg(bU).length, median: kvantil(dg(bU), 0.5), k1: kvantil(dg(bU), 0.25), k3: kvantil(dg(bU), 0.75) },
    ovrige: { n: dg(oU).length, median: kvantil(dg(oU), 0.5), k1: kvantil(dg(oU), 0.25), k3: kvantil(dg(oU), 0.75) },
  });
  const surv = (sett) => sett.map(r => {
    if (r.i) return { t: r.d_innst, event: 1, arsak: 1 };
    if (r.a) return { t: Math.round((D(r.avsl) - D(r.aapning)) / 86400000), event: 0, arsak: 2 };
    return { t: r.oppf, event: 0, arsak: 0 };
  });
  const sB = surv(bU), sO = surv(oU);
  const cB = cif(sB), cO = cif(sO);
  out("4b_km_og_cif_utforende_def", {
    km_median_bygg: kmMedian(sB), km_median_ovrige: kmMedian(sO),
    cif_50pst_bygg_dager: cifTid(cB, 0.5), cif_50pst_ovrige_dager: cifTid(cO, 0.5),
    cif_ved_365_bygg_pst: +(100 * cifVed(cB, 365)).toFixed(1),
    cif_ved_365_ovrige_pst: +(100 * cifVed(cO, 365)).toFixed(1),
  });

  // stratifisert medianforskjell (lane 1s spesifikasjon: >=10 innstilte i begge grupper per tingrett)
  const perRett = new Map();
  for (const r of rader) {
    const t = r.tingrett || "(uoppgitt)";
    (perRett.get(t) || perRett.set(t, []).get(t)).push(r);
  }
  const strata = [];
  for (const [t, d] of perRett) {
    if (t === "(uoppgitt)") continue;
    const bd = dg(d.filter(r => r.byggU_1)), od = dg(d.filter(r => !r.byggU_1));
    if (bd.length >= 10 && od.length >= 10)
      strata.push({ diff: kvantil(bd, 0.5) - kvantil(od, 0.5), vekt: bd.length + od.length });
  }
  const sv = strata.reduce((a, s) => a + s.vekt, 0);
  out("4c_stratifisert_mediandiff", {
    strata: strata.length, saker: sv,
    vektet_diff_dager: +(strata.reduce((a, s) => a + s.diff * s.vekt, 0) / sv).toFixed(1),
    strata_bygg_tregere: strata.filter(s => s.diff > 0).length,
  });

  // ---------- 5 MODNING (risikomengde) + naiv per kvartal — hentes fra 2023-09-01 og utover
  const modn = (await pool.query(`
    with s as materialized (
      select orgnr,
             min(dato) filter (where type = 'Konkurs - åpning') as aapning,
             min(dato) filter (where type = 'Konkurs - innstilling av bobehandlingen') as innst
      from kunngjoring.insolvens group by orgnr
    )
    select to_char(aapning,'YYYY-MM-DD') as aapning, to_char(innst,'YYYY-MM-DD') as innst
    from s where aapning >= date '${FRA}'`)).rows;
  for (const r of modn) {
    r.oppf = Math.round((D(korpusslutt) - D(r.aapning)) / 86400000);
    r.d = r.innst && r.innst >= r.aapning ? Math.round((D(r.innst) - D(r.aapning)) / 86400000) : null;
  }
  const hor = (m) => {
    const g = m * 30.44, ris = modn.filter(r => r.oppf >= g);
    return { mnd: m, n: ris.length, pst: pst(ris.filter(r => r.d !== null && r.d <= g).length, ris.length) };
  };
  out("5_modning_risikomengde", [3, 6, 12, 18, 24, 30].map(hor));
  const kv = new Map();
  for (const r of modn) {
    const k = r.aapning.slice(0, 4) + "K" + (Math.floor((+r.aapning.slice(5, 7) - 1) / 3) + 1);
    const e = kv.get(k) || { n: 0, i: 0 }; e.n++; if (r.innst) e.i++; kv.set(k, e);
  }
  out("5b_naiv_per_kvartal", [...kv].sort().map(([k, e]) => ({ kvartal: k, n: e.n, pst: pst(e.i, e.n) })));

  // ---------- 6 VINDUSFØLSOMHET (tre kontrollvinduer)
  const vinduer = [["2023-09-01", "2025-06-30"], ["2023-09-01", "2025-12-31"], ["2023-09-01", korpusslutt]];
  out("6_vindusfolsomhet", vinduer.map(([f, t]) => {
    const d = modn.filter(r => r.aapning >= f && r.aapning <= t);
    return { vindu: f + ".." + t, n: d.length, innstilt_pst: pst(d.filter(r => r.innst).length, d.length) };
  }));

  // ---------- 7 DOMSTOLER: n>=100-porten, spennet, navn-vs-saksnrkode
  const kode = (s) => {
    if (!s) return null;
    const m = /KON-+([A-Z0-9]+)/.exec(s.replace(/KJENNELSE.*$/, ""));
    return m ? m[1] : null;
  };
  const rett = [...perRett].map(([t, d]) => {
    const i = d.filter(r => r.i).length;
    return { tingrett: t, saker: d.length, innstilt_pst: pst(i, d.length),
             median: kvantil(dg(d), 0.5), byggandel_pst: pst(d.filter(r => r.byggU_1).length, d.length) };
  }).sort((a, b) => b.saker - a.saker);
  const store = rett.filter(r => r.saker >= 100);
  const parNavnKode = new Map(), parKodeNavn = new Map();
  let uenigNavnKode = 0, utenKode = 0;
  for (const r of rader) {
    const k = kode(r.saksnr);
    if (!k) { utenKode++; continue; }
    const t = r.tingrett || "?";
    if (!parNavnKode.has(t)) parNavnKode.set(t, new Set());
    parNavnKode.get(t).add(k);
    if (!parKodeNavn.has(k)) parKodeNavn.set(k, new Set());
    parKodeNavn.get(k).add(t);
  }
  for (const [, s] of parNavnKode) if (s.size > 1) uenigNavnKode++;
  out("7_domstoler", {
    distinkte_navn_i_vinduet: perRett.size,
    n100: store.length,
    spenn_innstilt_pst: [Math.min(...store.map(r => r.innstilt_pst)), Math.max(...store.map(r => r.innstilt_pst))],
    spenn_median_dager: [Math.min(...store.map(r => r.median)), Math.max(...store.map(r => r.median))],
    byggandel_spenn_pst: [Math.min(...store.map(r => r.byggandel_pst)), Math.max(...store.map(r => r.byggandel_pst))],
    navn_med_flere_koder: uenigNavnKode, koder: parKodeNavn.size,
    koder_med_flere_navn: [...parKodeNavn.values()].filter(s => s.size > 1).length,
    aapningsrader_uten_parsebar_kode: utenKode,
    n100_liste: store.map(r => ({ tingrett: r.tingrett, saker: r.saker, pst: r.innstilt_pst, median: r.median })),
  });

  // ---------- 8 SENSUS + SERIER + L1 + SLETTEKRYSS
  out("8_sensus_aapningsraden", {
    bransje: rader.filter(r => r.bransje).length,
    tingrett: rader.filter(r => r.tingrett).length,
    saksnr: rader.filter(r => r.saksnr).length,
    bostyrer: rader.filter(r => r.har_bostyrer).length,
    fristdag: rader.filter(r => r.har_fristdag).length,
    kapital: rader.filter(r => r.har_kapital).length,
    av: n,
  });
  const mnd = (await pool.query(`
    select to_char(date_trunc('month', dato),'YYYY-MM') as m,
           count(distinct dato) as dager, count(distinct orgnr) as selskaper
    from kunngjoring.insolvens
    where type = 'Konkurs - innstilling av bobehandlingen' group by 1 order by 1`)).rows;
  const kjerne = mnd.filter(r => r.m >= "2023-09" && r.m <= "2026-07");
  out("8b_innstillingsserien_maaneder", {
    forste_maaned: mnd[0], antall_maaneder_2023_09_til_2026_07: kjerne.length,
    dager_min: Math.min(...kjerne.map(r => +r.dager)), dager_maks: Math.max(...kjerne.map(r => +r.dager)),
    selskaper_min: Math.min(...kjerne.map(r => +r.selskaper)), selskaper_maks: Math.max(...kjerne.map(r => +r.selskaper)),
  });
  const l1 = (await pool.query(`
    with s as materialized (
      select orgnr,
             min(dato) filter (where type = 'Konkurs - åpning') as aapning,
             min(dato) filter (where type = 'Konkurs - innstilling av bobehandlingen') as innst
      from kunngjoring.insolvens group by orgnr
    )
    select count(*) filter (where innst is not null) as innstillingsselskaper,
           count(*) filter (where innst is not null and aapning is null) as uten_aapning,
           count(*) filter (where innst is not null and aapning < date '${FRA}') as aapnet_foer_vinduet
    from s`)).rows[0];
  out("8c_L1_innstillinger_uten_aapning", l1);
  const utf = rader.filter(r => r.i || r.a), aap = rader.filter(r => !r.i && !r.a);
  out("8d_slettekryss_utfallsserien", {
    med_utfall: utf.length, med_utfall_slettet_i_reg: utf.filter(r => r.slettet_i_reg).length,
    apne: aap.length, apne_med_slettkunngjoring: aap.filter(r => r.har_slettkunngj).length,
    apne_slettet_i_reg: aap.filter(r => r.slettet_i_reg).length,
  });

  // ---------- 9 hva har de «fortsatt åpne» av senere insolvenshendelser?
  const apneTyper = (await pool.query(`
    with s as materialized (
      select orgnr,
             min(dato) filter (where type = 'Konkurs - åpning') as aapning,
             min(dato) filter (where type = 'Konkurs - innstilling av bobehandlingen') as innst,
             min(dato) filter (where type = 'Konkurs - avslutning av bobehandlingen') as avsl
      from kunngjoring.insolvens group by orgnr
    ),
    apen as materialized (
      select orgnr, aapning from s
      where aapning between date '${FRA}' and date '${TIL}' and innst is null and avsl is null
    )
    select i.type, count(distinct i.orgnr) as selskaper
    from kunngjoring.insolvens i join apen a on a.orgnr = i.orgnr and i.dato >= a.aapning
    group by 1 having count(distinct i.orgnr) >= 3 order by 2 desc`)).rows;
  out("9_apne_bo_senere_hendelser", apneTyper);

  const j = JSON.stringify({ kjort: KJORT, korpusslutt, resultater: res }, null, 1);
  writeFileSync(`${DATA}/kontroll-kjerne-${KJORT}.json`, j, "utf8");
  console.log(`\nskrev data/kontroll-kjerne-${KJORT}.json sha256=` +
    createHash("sha256").update(j).digest("hex"));
} catch (e) { console.error("KONTROLLFEIL:", e.message, e.stack); process.exitCode = 1; }
finally { await closePool(); }
