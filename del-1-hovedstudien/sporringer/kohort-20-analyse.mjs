// LANE 1 / kohort — HOVEDANALYSE (READ-ONLY, kun SELECT).
//
// Produserer: hovedtall, bransjetabell, domstolstabell, varigheter (raa + stratifisert
// paa tingrett), modningskurve, vindusfolsomhet. Frosne uttrekk til data/, figurgrunnlag
// til figurer/. Alt aggregert: ingen orgnr, ingen navn, ingen bostyrere forlater skriptet.
//
// Bindende regler brukt her:
//   L8/L14  alle tellinger er count(distinct orgnr); kohort via forste aapning per selskap
//   L5      utfylling maales med nullif(trim(...),'')
//   L16     utfall leses fra kunngjoringene, ALDRI fra company_intel.livslop
//   L17     bransje-etiketten slaas opp mot BEGGE naeringsvintager (SN2007/SN2025)
//   L1      ingen tidsserie for konkurs trekkes ut av dette materialet
import { getPool, closePool } from "./db.mjs";
import { writeFileSync } from "node:fs";
import { createHash } from "node:crypto";
import { slaaOpp, erByggF, erByggUtforende, IKKE_NAERING } from "./kohort-bransjeklassifikator.mjs";

const DATA = "./data";
const FIG = "./figurer";
const KJORT = new Date().toISOString().slice(0, 10);
const FRA = "2023-09-01", TIL = "2024-12-31";

const pool = getPool();
const sha = (s) => createHash("sha256").update(s).digest("hex");
const out = (l, r) => { console.log("\n=== " + l + " ==="); console.log(JSON.stringify(r, null, 1)); };
const pst = (a, b) => (b ? +(100 * a / b).toFixed(1) : null);

const skrevet = [];
function skrivCsv(sti, rader) {
  const kol = rader.length ? Object.keys(rader[0]) : [];
  const esc = (v) => v === null || v === undefined ? ""
    : (/[",\n;]/.test(String(v)) ? '"' + String(v).replace(/"/g, '""') + '"' : String(v));
  const csv = [kol.join(";"), ...rader.map(r => kol.map(k => esc(r[k])).join(";"))].join("\n") + "\n";
  writeFileSync(sti, csv, "utf8");
  const h = sha(csv);
  skrevet.push({ fil: sti, rader: rader.length, sha256: h });
  return h;
}
function kvantil(arr, q) {
  if (!arr.length) return null;
  const s = arr.slice().sort((a, b) => a - b);
  const i = (s.length - 1) * q, lo = Math.floor(i), hi = Math.ceil(i);
  return lo === hi ? s[lo] : +(s[lo] + (s[hi] - s[lo]) * (i - lo)).toFixed(1);
}
// Clopper-Pearson via inverse beta (Newton paa regularisert ufullstendig beta).
function betacf(a, b, x) {
  const MAXIT = 300, EPS = 3e-14, FPMIN = 1e-300;
  const qab = a + b, qap = a + 1, qam = a - 1;
  let c = 1, d = 1 - qab * x / qap;
  if (Math.abs(d) < FPMIN) d = FPMIN;
  d = 1 / d; let h = d;
  for (let m = 1; m <= MAXIT; m++) {
    const m2 = 2 * m;
    let aa = m * (b - m) * x / ((qam + m2) * (a + m2));
    d = 1 + aa * d; if (Math.abs(d) < FPMIN) d = FPMIN;
    c = 1 + aa / c; if (Math.abs(c) < FPMIN) c = FPMIN;
    d = 1 / d; h *= d * c;
    aa = -(a + m) * (qab + m) * x / ((a + m2) * (qap + m2));
    d = 1 + aa * d; if (Math.abs(d) < FPMIN) d = FPMIN;
    c = 1 + aa / c; if (Math.abs(c) < FPMIN) c = FPMIN;
    d = 1 / d; const del = d * c; h *= del;
    if (Math.abs(del - 1) < EPS) break;
  }
  return h;
}
const gammln = (x) => {
  const c = [76.18009172947146, -86.50532032941677, 24.01409824083091,
             -1.231739572450155, 0.1208650973866179e-2, -0.5395239384953e-5];
  let y = x, tmp = x + 5.5; tmp -= (x + 0.5) * Math.log(tmp);
  let ser = 1.000000000190015;
  for (let j = 0; j < 6; j++) ser += c[j] / ++y;
  return -tmp + Math.log(2.5066282746310005 * ser / x);
};
function ibeta(a, b, x) {
  if (x <= 0) return 0; if (x >= 1) return 1;
  const bt = Math.exp(gammln(a + b) - gammln(a) - gammln(b) + a * Math.log(x) + b * Math.log(1 - x));
  return x < (a + 1) / (a + b + 2) ? bt * betacf(a, b, x) / a : 1 - bt * betacf(b, a, 1 - x) / b;
}
function invIbeta(a, b, p) {
  let lo = 0, hi = 1;
  for (let i = 0; i < 200; i++) { const m = (lo + hi) / 2; (ibeta(a, b, m) < p ? lo = m : hi = m); }
  return (lo + hi) / 2;
}
function clopperPearson(k, n, alpha = 0.05) {
  if (!n) return [null, null];
  const lo = k === 0 ? 0 : invIbeta(k, n - k + 1, alpha / 2);
  const hi = k === n ? 1 : invIbeta(k + 1, n - k, 1 - alpha / 2);
  return [+(100 * lo).toFixed(1), +(100 * hi).toFixed(1)];
}

const SQL = `
with aapning as materialized (
  select orgnr, min(dato) as aapning
  from kunngjoring.insolvens where type = 'Konkurs - åpning' group by orgnr
),
kohort as materialized (
  select orgnr, aapning from aapning where aapning >= $1::date
),
attr as materialized (
  select i.orgnr,
         nullif(trim(i.bransje),'')  as bransje,
         nullif(trim(i.tingrett),'') as tingrett
  from kunngjoring.insolvens i
  join kohort k on k.orgnr = i.orgnr and i.dato = k.aapning
  where i.type = 'Konkurs - åpning'
),
innst as materialized (
  select orgnr, min(dato) as forste from kunngjoring.insolvens
  where type = 'Konkurs - innstilling av bobehandlingen' group by orgnr
),
avsl as materialized (
  select orgnr, min(dato) as forste from kunngjoring.insolvens
  where type = 'Konkurs - avslutning av bobehandlingen' group by orgnr
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
select to_char(k.aapning,'YYYY-MM-DD') as aapning,
       a.bransje, a.tingrett,
       to_char(ie.dato,'YYYY-MM-DD') as innstilling,
       to_char(ae.dato,'YYYY-MM-DD') as avslutning,
       (ie.dato - k.aapning) as d_innst,
       (ae.dato - k.aapning) as d_avsl,
       (i.forste  < k.aapning) as innst_for_aapning,
       (av.forste < k.aapning) as avsl_for_aapning
from kohort k
left join attr a        on a.orgnr = k.orgnr
left join innst i       on i.orgnr = k.orgnr
left join avsl av       on av.orgnr = k.orgnr
left join innst_etter ie on ie.orgnr = k.orgnr
left join avsl_etter ae  on ae.orgnr = k.orgnr
`;

try {
  await pool.query("set statement_timeout = '900s'");
  const korpusslutt = (await pool.query("select to_char(max(dato),'YYYY-MM-DD') d from kunngjoring.insolvens")).rows[0].d;
  const t0 = Date.now();
  // Hentegulvet er 2023-08-25 (forste innstillingskunngjoring i korpuset), ikke 2023-09-01,
  // slik at briefens alternative vindu 2023-08-24.. kan reproduseres uten ny spørring.
  const HENT_FRA = "2023-08-24";
  const alle = (await pool.query(SQL, [HENT_FRA])).rows;
  console.log(`hentet ${alle.length} aapninger fra ${HENT_FRA} paa ${((Date.now() - t0) / 1000).toFixed(1)} s; korpusslutt ${korpusslutt}`);

  for (const r of alle) {
    const t = slaaOpp(r.bransje);
    r.nace = t.kode; r.kilde = t.kilde;
    r.byggF = erByggF(r.nace); r.byggU = erByggUtforende(r.nace);
    r.utfall = r.innstilling && r.avslutning ? "begge" : r.innstilling ? "innstilt"
             : r.avslutning ? "avsluttet" : "fortsatt_apen";
    r.oppfolging_dager = Math.round((Date.parse(korpusslutt) - Date.parse(r.aapning)) / 86400000);
  }
  const kohort = alle.filter(r => r.aapning >= FRA && r.aapning <= TIL);
  const modningsgrunnlag = alle.filter(r => r.aapning >= FRA);  // kurven starter der vinduet starter

  // ---------------------------------------------------------------- 1 HOVEDTALL
  const grupper = (rad) => [
    ["ALLE", () => true],
    ["BYGG utforende (41.2/41.0 + 42 + 43)", (r) => r.byggU],
    ["BYGG SN2007-omraade F (41+42+43)", (r) => r.byggF],
    ["herav eiendomsutvikling SN2007 41.1", (r) => r.nace && /^41\.1/.test(r.nace)],
    ["OVRIGE naeringer (ikke utforende bygg)", (r) => !r.byggU],
    ["uten naeringskode", (r) => !r.nace],
  ];
  function tabell(sett) {
    return grupper().map(([navn, f]) => {
      const d = sett.filter(f), n = d.length;
      const i = d.filter(r => r.innstilling).length, a = d.filter(r => r.avslutning).length;
      const b = d.filter(r => r.innstilling && r.avslutning).length;
      const o = d.filter(r => !r.innstilling && !r.avslutning).length;
      const ki = clopperPearson(i, n);
      return { gruppe: navn, aapninger: n, innstilt: i, innstilt_pst: pst(i, n),
               innstilt_ki95_lav: ki[0], innstilt_ki95_hoy: ki[1],
               avsluttet: a, avsluttet_pst: pst(a, n), begge_kunngjoringer: b,
               fortsatt_apne: o, fortsatt_apne_pst: pst(o, n) };
    });
  }
  const hoved = tabell(kohort);
  out("1 — HOVEDTALL, kohort " + FRA + ".." + TIL, hoved);
  skrivCsv(`${DATA}/kohort-hovedtall-${KJORT}.csv`, hoved);

  out("oppfolgingstid i kohorten (dager fra aapning til korpusslutt " + korpusslutt + ")", {
    minimum: Math.min(...kohort.map(r => r.oppfolging_dager)),
    minimum_mnd: +(Math.min(...kohort.map(r => r.oppfolging_dager)) / 30.44).toFixed(1),
    median: kvantil(kohort.map(r => r.oppfolging_dager), 0.5),
    maksimum: Math.max(...kohort.map(r => r.oppfolging_dager)),
  });

  const feilrekkefolge = kohort.filter(r => r.innst_for_aapning || r.avsl_for_aapning);
  out("selskaper med utfallskunngjoring FOR sin forste aapning (tidligere konkurs hvis aapningskunngjoring er utgatt, L1)", {
    antall: feilrekkefolge.length,
    fortsatt_klassifisert_innstilt_etterpaa: feilrekkefolge.filter(r => r.innstilling).length,
    mister_utfall_naar_vi_krever_dato_etter_aapning: feilrekkefolge.filter(r => !r.innstilling && !r.avslutning).length,
  });

  // ---------------------------------------------------------------- 2 BRANSJETABELL
  const perBransje = new Map();
  for (const r of kohort) {
    const n = r.bransje || "(uoppgitt)";
    const e = perBransje.get(n) || { bransje_etikett: n, nace: r.nace, aapninger: 0, innstilt: 0, avsluttet: 0, apne: 0 };
    e.aapninger++; if (r.innstilling) e.innstilt++; if (r.avslutning) e.avsluttet++;
    if (!r.innstilling && !r.avslutning) e.apne++;
    perBransje.set(n, e);
  }
  const bransjeRader = [...perBransje.values()].map(e => {
    const ki = clopperPearson(e.innstilt, e.aapninger);
    return { ...e, er_bygg_utforende: erByggUtforende(e.nace) ? 1 : 0, er_bygg_F: erByggF(e.nace) ? 1 : 0,
             innstilt_pst: pst(e.innstilt, e.aapninger), ki95_lav: ki[0], ki95_hoy: ki[1],
             publiserbar: e.aapninger >= 10 ? 1 : 0 };
  }).sort((a, b) => b.aapninger - a.aapninger);
  // Tynne celler (n < 10) slaas sammen til en restrad slik at totalene fortsatt gaar opp,
  // men ingen enkeltbedrifts utfall kan leses ut av en rad med n = 1.
  const tynne = bransjeRader.filter(r => r.aapninger < 10);
  const restrad = { bransje_etikett: `(${tynne.length} etiketter med under 10 aapninger, slaatt sammen)`,
    nace: "", aapninger: tynne.reduce((a, r) => a + r.aapninger, 0),
    innstilt: tynne.reduce((a, r) => a + r.innstilt, 0),
    avsluttet: tynne.reduce((a, r) => a + r.avsluttet, 0), apne: tynne.reduce((a, r) => a + r.apne, 0),
    er_bygg_utforende: "", er_bygg_F: "", ki95_lav: "", ki95_hoy: "", publiserbar: 1 };
  restrad.innstilt_pst = pst(restrad.innstilt, restrad.aapninger);
  skrivCsv(`${DATA}/kohort-per-bransje-${KJORT}.csv`,
           [...bransjeRader.filter(r => r.aapninger >= 10), restrad]);
  out("2 — BYGGFAG med minst 30 aapninger (kohortvinduet)",
      bransjeRader.filter(r => r.er_bygg_F && r.aapninger >= 30)
        .map(({ bransje_etikett, nace, aapninger, innstilt, innstilt_pst, ki95_lav, ki95_hoy }) =>
             ({ bransje_etikett, nace, aapninger, innstilt, innstilt_pst, ki95_lav, ki95_hoy })));

  // Reproduksjon av briefens bransjetall (vindu 2023-08-24..2024-12-31)
  const briefVindu = alle.filter(r => r.aapning >= "2023-08-24" && r.aapning <= TIL);
  const briefKontroll = ["Snekkerarbeid", "Grunnarbeid", "Malerarbeid",
                         "Elektrisk installasjonsarbeid", "Oppføring av bygninger", "Rørleggerarbeid"]
    .map(b => {
      const d = briefVindu.filter(r => (r.bransje || "").split("\n")[0].trim() === b);
      const i = d.filter(r => r.innstilling).length;
      return { bransje: b, aapninger: d.length, innstilt: i, innstilt_pst: pst(i, d.length) };
    });
  out("2b — reproduksjon av briefens bransjetall (vindu 2023-08-24..2024-12-31)", briefKontroll);

  // ---------------------------------------------------------------- 3 DOMSTOLER
  const perRett = new Map();
  for (const r of kohort) {
    const n = r.tingrett || "(uoppgitt)";
    const e = perRett.get(n) || { tingrett: n, saker: 0, innstilt: 0, avsluttet: 0, apne: 0, bygg: 0, dager: [] };
    e.saker++; if (r.innstilling) { e.innstilt++; e.dager.push(r.d_innst); }
    if (r.avslutning) e.avsluttet++; if (!r.innstilling && !r.avslutning) e.apne++;
    if (r.byggU) e.bygg++;
    perRett.set(n, e);
  }
  const rettRader = [...perRett.values()].map(e => {
    const ki = clopperPearson(e.innstilt, e.saker);
    return { tingrett: e.tingrett, saker: e.saker, innstilt: e.innstilt, innstilt_pst: pst(e.innstilt, e.saker),
             ki95_lav: ki[0], ki95_hoy: ki[1], avsluttet: e.avsluttet, fortsatt_apne: e.apne,
             byggandel_pst: pst(e.bygg, e.saker),
             median_dager_til_innstilling: kvantil(e.dager, 0.5),
             kvartil1_dager: kvantil(e.dager, 0.25), kvartil3_dager: kvantil(e.dager, 0.75),
             publiserbar: e.saker >= 10 ? 1 : 0 };
  }).sort((a, b) => b.saker - a.saker);
  skrivCsv(`${DATA}/kohort-per-tingrett-${KJORT}.csv`, rettRader.filter(r => r.saker >= 10));
  out("3 — DOMSTOLER med minst 100 saker", rettRader.filter(r => r.saker >= 100));
  out("3b — antall distinkte tingrettsnavn i vinduet (navnedrift?)",
      { distinkte: perRett.size, med_under_100_saker: rettRader.filter(r => r.saker < 100).length });

  // ---------------------------------------------------------------- 4 VARIGHET
  const dager = (sett) => sett.filter(r => r.innstilling && r.d_innst !== null).map(r => r.d_innst);
  const varighet = (navn, sett) => {
    const d = dager(sett);
    return { gruppe: navn, n: d.length, median: kvantil(d, 0.5),
             kvartil1: kvantil(d, 0.25), kvartil3: kvantil(d, 0.75),
             p10: kvantil(d, 0.10), p90: kvantil(d, 0.90) };
  };
  const varigheter = [
    varighet("ALLE", kohort),
    varighet("BYGG utforende", kohort.filter(r => r.byggU)),
    varighet("BYGG SN2007-F", kohort.filter(r => r.byggF)),
    varighet("OVRIGE (ikke utforende bygg)", kohort.filter(r => !r.byggU)),
  ];
  out("4 — VARIGHET aapning -> innstilling (dager), raa", varigheter);
  skrivCsv(`${DATA}/kohort-varighet-raa-${KJORT}.csv`, varigheter);

  // Stratifisert paa tingrett: differansen bygg - ovrige beregnes INNENFOR hver domstol
  // og vektes med domstolens saksvolum. Dette er kravet fra briefen: bygg er ujevnt
  // fordelt mellom domstolene, saa en raa medianforskjell kan vaere en domstolseffekt.
  const strata = [];
  for (const [navn, e] of perRett) {
    if (navn === "(uoppgitt)") continue;
    const d = kohort.filter(r => (r.tingrett || "(uoppgitt)") === navn);
    const bd = dager(d.filter(r => r.byggU)), od = dager(d.filter(r => !r.byggU));
    if (bd.length >= 10 && od.length >= 10) {
      strata.push({ tingrett: navn, n_bygg: bd.length, n_ovrig: od.length,
                    median_bygg: kvantil(bd, 0.5), median_ovrig: kvantil(od, 0.5),
                    differanse: +(kvantil(bd, 0.5) - kvantil(od, 0.5)).toFixed(1),
                    vekt: bd.length + od.length });
    }
  }
  const sumVekt = strata.reduce((a, s) => a + s.vekt, 0);
  const vektetDiff = +(strata.reduce((a, s) => a + s.differanse * s.vekt, 0) / sumVekt).toFixed(1);
  const raaDiff = +(varigheter[1].median - varigheter[3].median).toFixed(1);
  out("4b — TINGRETT-STRATIFISERT medianforskjell bygg vs ovrige", {
    strata_med_minst_10_i_begge: strata.length, saker_i_strata: sumVekt,
    raa_differanse_dager: raaDiff, vektet_stratifisert_differanse_dager: vektetDiff,
    strata_der_bygg_er_tregere: strata.filter(s => s.differanse > 0).length,
    strata_der_bygg_er_raskere: strata.filter(s => s.differanse < 0).length,
  });
  skrivCsv(`${DATA}/kohort-varighet-stratifisert-${KJORT}.csv`, strata.sort((a, b) => b.vekt - a.vekt));

  // ---------------------------------------------------------------- 5 MODNINGSKURVE
  // Risikomengde-form: for horisont m maaneder telles bare bo som HAR minst m maaneders
  // oppfolging. Dette er aerlighetsutstillingen mot hoyresensurering.
  const maksOppf = Math.max(...modningsgrunnlag.map(r => r.oppfolging_dager));
  const kurve = [];
  for (let m = 0; m * 30.44 <= maksOppf; m++) {
    const grense = m * 30.44;
    const rad = { maaneder: m };
    for (const [navn, f] of [["alle", () => true], ["bygg", (r) => r.byggU], ["ovrige", (r) => !r.byggU]]) {
      const risiko = modningsgrunnlag.filter(r => f(r) && r.oppfolging_dager >= grense);
      const hendt = risiko.filter(r => r.d_innst !== null && r.d_innst <= grense).length;
      rad[`n_${navn}`] = risiko.length;
      rad[`innstilt_${navn}`] = hendt;
      rad[`andel_${navn}_pst`] = pst(hendt, risiko.length);
    }
    kurve.push(rad);
  }
  skrivCsv(`${FIG}/modningskurve-risikomengde-${KJORT}.csv`, kurve);
  out("5 — MODNINGSKURVE (risikomengde), utvalgte horisonter",
      kurve.filter(r => [3, 6, 9, 12, 18, 24, 30, 36].includes(r.maaneder)));

  // Naiv form: andel innstilt per aapningskvartal slik den ser ut i dag. Viser den
  // mekaniske nedgangen for ferske kvartaler — figuren som ikke skal skjules.
  const perKv = new Map();
  for (const r of modningsgrunnlag) {
    const kv = r.aapning.slice(0, 4) + "K" + (Math.floor((+r.aapning.slice(5, 7) - 1) / 3) + 1);
    const e = perKv.get(kv) || { aapning_kvartal: kv, aapninger: 0, innstilt: 0, bygg: 0, bygg_innstilt: 0, oppf: [] };
    e.aapninger++; if (r.innstilling) e.innstilt++;
    if (r.byggU) { e.bygg++; if (r.innstilling) e.bygg_innstilt++; }
    e.oppf.push(r.oppfolging_dager); perKv.set(kv, e);
  }
  const kvRader = [...perKv.values()].map(e => ({
    aapning_kvartal: e.aapning_kvartal, aapninger: e.aapninger,
    median_oppfolging_dager: kvantil(e.oppf, 0.5),
    innstilt: e.innstilt, innstilt_pst: pst(e.innstilt, e.aapninger),
    bygg_aapninger: e.bygg, bygg_innstilt_pst: pst(e.bygg_innstilt, e.bygg),
  })).sort((a, b) => a.aapning_kvartal.localeCompare(b.aapning_kvartal));
  skrivCsv(`${FIG}/modningskurve-naiv-per-kvartal-${KJORT}.csv`, kvRader);
  out("5b — NAIV andel innstilt per aapningskvartal (hoyresensurering synliggjort)", kvRader);

  // ---------------------------------------------------------------- 6 VINDUSFOLSOMHET
  const vinduer = [
    ["2023-09-01", "2024-06-30"], ["2023-09-01", "2024-12-31"], ["2023-08-25", "2024-12-31"],
    ["2023-09-01", "2025-06-30"], ["2023-09-01", "2025-12-31"], ["2023-09-01", korpusslutt],
    ["2024-01-01", "2024-12-31"], ["2023-09-01", "2024-03-31"],
  ];
  const folsomhet = vinduer.map(([f, t]) => {
    const d = alle.filter(r => r.aapning >= f && r.aapning <= t);
    const i = d.filter(r => r.innstilling).length;
    const bu = d.filter(r => r.byggU), bi = bu.filter(r => r.innstilling).length;
    const ki = clopperPearson(i, d.length);
    return { vindu_fra: f, vindu_til: t, aapninger: d.length,
             min_oppfolging_dager: d.length ? Math.min(...d.map(r => r.oppfolging_dager)) : null,
             innstilt: i, innstilt_pst: pst(i, d.length), ki95_lav: ki[0], ki95_hoy: ki[1],
             avsluttet_pst: pst(d.filter(r => r.avslutning).length, d.length),
             apne_pst: pst(d.filter(r => !r.innstilling && !r.avslutning).length, d.length),
             bygg_aapninger: bu.length, bygg_innstilt_pst: pst(bi, bu.length) };
  });
  out("6 — VINDUSFOLSOMHET", folsomhet);
  skrivCsv(`${DATA}/kohort-vindusfolsomhet-${KJORT}.csv`, folsomhet);

  // ---------------------------------------------------------------- 7 SERIEDEKNING (internt)
  const seriedekning = (await pool.query(`
    with aapning as materialized (
      select orgnr, min(dato) as d from kunngjoring.insolvens where type='Konkurs - åpning' group by orgnr
    ),
    innst as materialized (
      select orgnr, min(dato) as d from kunngjoring.insolvens
      where type='Konkurs - innstilling av bobehandlingen' group by orgnr
    )
    select count(*) as innstillinger_totalt,
           count(*) filter (where a.orgnr is null) as uten_aapning_i_korpuset,
           count(*) filter (where a.orgnr is not null and a.d < date '2023-09-01') as aapnet_for_vinduet,
           count(*) filter (where a.orgnr is not null and a.d >= date '2023-09-01') as aapnet_i_eller_etter_vinduet
    from innst i left join aapning a on a.orgnr = i.orgnr
  `)).rows[0];
  out("7 — innstillinger uten aapningskunngjoring i korpuset (maaler L1-hullet i AAPNINGSserien)", seriedekning);

  const dagsdekning = (await pool.query(`
    select to_char(date_trunc('month', dato),'YYYY-MM') as maaned,
           count(distinct dato) as dager_med_kunngjoring,
           count(distinct orgnr) as selskaper
    from kunngjoring.insolvens
    where type='Konkurs - innstilling av bobehandlingen'
    group by 1 order by 1
  `)).rows.map(r => ({ ...r, dager_med_kunngjoring: Number(r.dager_med_kunngjoring), selskaper: Number(r.selskaper) }));
  skrivCsv(`${DATA}/innstillingsserie-manedsdekning-${KJORT}.csv`, dagsdekning);
  out("7b — innstillingsserien per maaned (hull i serien ville vise seg som faa dager/faa selskaper)",
      dagsdekning.filter(r => r.maaned >= "2023-08"));

  // ------------------------------------------- 8 UAVHENGIG DEKNINGSPROVE PAA UTFALLSSERIEN
  // Dekningen av utfallsserien kan ikke maales mot kilden herfra. Men den kan testes
  // INNENFRA mot en uavhengig hendelse: naar et bo er sluttbehandlet, slettes selskapet
  // fra registeret. Et bo vi tror er «fortsatt aapent», men der selskapet ER slettet, er
  // en kandidat for en utfallskunngjoring vi ikke har. Slettingsserien er en annen
  // kunngjoringstype, hentet uavhengig av innstillingsserien.
  const dekning = (await pool.query(`
    with aapning as materialized (
      select orgnr, min(dato) as d from kunngjoring.insolvens where type='Konkurs - åpning' group by orgnr
    ),
    kohort as materialized (
      select orgnr, d from aapning where d between $1::date and $2::date
    ),
    innst as materialized (
      select distinct orgnr from kunngjoring.insolvens where type='Konkurs - innstilling av bobehandlingen'
    ),
    avsl as materialized (
      select distinct orgnr from kunngjoring.insolvens where type='Konkurs - avslutning av bobehandlingen'
    ),
    slett as materialized (
      select orgnr, min(dato) as d from kunngjoring.insolvens where type='Sletting' group by orgnr
    )
    select case when i.orgnr is not null or a.orgnr is not null then 'har utfallskunngjoring'
                else 'fortsatt aapent' end as tilstand,
           count(*) as bo,
           count(*) filter (where s.orgnr is not null) as med_slettingskunngjoring,
           count(*) filter (where c.is_deleted) as slettet_i_registeret,
           count(*) filter (where s.orgnr is null and not coalesce(c.is_deleted,false)) as verken_slettet_eller_utfall
    from kohort k
    left join innst i on i.orgnr = k.orgnr
    left join avsl a  on a.orgnr = k.orgnr
    left join slett s on s.orgnr = k.orgnr
    left join company_intel.company c on c.orgnr = k.orgnr
    group by 1 order by 1
  `, [FRA, TIL])).rows;
  out("8 — UAVHENGIG DEKNINGSPROVE: er de «fortsatt aapne» boene virkelig aapne?", dekning);

  // ------------------------------------------- 9 PUBLISERBARE AGGREGATER (n >= 10)
  skrivCsv(`${DATA}/PUBLISERBAR-per-bransje-${KJORT}.csv`,
    bransjeRader.filter(r => r.aapninger >= 10).map(({ bransje_etikett, nace, er_bygg_utforende, aapninger, innstilt, innstilt_pst, ki95_lav, ki95_hoy, avsluttet, apne }) =>
      ({ bransje_etikett, nace, er_bygg_utforende, aapninger, innstilt, innstilt_pst, ki95_lav, ki95_hoy, avsluttet, fortsatt_apne: apne })));
  skrivCsv(`${DATA}/PUBLISERBAR-per-tingrett-${KJORT}.csv`, rettRader.filter(r => r.saker >= 10).map(({ publiserbar, ...r }) => r));
  const byggRett = rettRader.filter(r => r.saker >= 100).map(r => {
    const d = kohort.filter(x => (x.tingrett || "(uoppgitt)") === r.tingrett);
    const b = d.filter(x => x.byggU), o = d.filter(x => !x.byggU);
    const bi = b.filter(x => x.innstilling).length, oi = o.filter(x => x.innstilling).length;
    return { tingrett: r.tingrett, bygg_saker: b.length, bygg_innstilt_pst: pst(bi, b.length),
             ovrige_saker: o.length, ovrige_innstilt_pst: pst(oi, o.length),
             bygg_median_dager: kvantil(b.filter(x => x.innstilling).map(x => x.d_innst), 0.5),
             ovrige_median_dager: kvantil(o.filter(x => x.innstilling).map(x => x.d_innst), 0.5) };
  }).filter(r => r.bygg_saker >= 10 && r.ovrige_saker >= 10);
  skrivCsv(`${DATA}/PUBLISERBAR-bygg-per-tingrett-${KJORT}.csv`, byggRett);
  out("9 — publiserbare aggregater skrevet (alle celler n >= 10)",
      { bransjerader: bransjeRader.filter(r => r.aapninger >= 10).length,
        tingrettsrader: rettRader.filter(r => r.saker >= 10).length,
        bygg_x_tingrett: byggRett.length });

  // ---------------------------------------------------------------- kvittering
  const kvittering = { studie: "Tomme bo — LANE 1", kjoredato: KJORT, korpusslutt,
                       kohortvindu: { fra: FRA, til: TIL }, kohort_n: kohort.length,
                       sporring_sha256: sha(SQL), filer: skrevet };
  const kj = JSON.stringify(kvittering, null, 1);
  writeFileSync(`${DATA}/kohort-kvittering-${KJORT}.json`, kj, "utf8");
  out("FILER SKREVET", skrevet.map(f => ({ fil: f.fil.split("/").pop(), rader: f.rader, sha256: f.sha256.slice(0, 16) + "..." })));
} catch (e) { console.error("FEIL:", e.message, e.stack); } finally { await closePool(); }
