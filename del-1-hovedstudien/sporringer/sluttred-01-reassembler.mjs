// SLUTTREDAKSJON — reassemblering av publiseringsfilene (READ-ONLY, kun SELECT).
//
// Utfører talljournalens MAA-FIKSES 2 og tallrevisjonens kritiske defekt:
//   (a) publiserte tabeller faar TO utfallskolonner — innstilt og ikke_innstilt —
//       begge >= 10, ellers restrad;
//   (b) domstolstabellene publiserer kun kretser med n >= 100 (16 kretser);
//   (c) byggsplitten for Nord-Troms og Senja strykes (ikke-innstilt bygg = 6 < 10);
//   (d) uklassifiserbar naeringsangivelse publiseres som 155-botta, aldri delmengder;
//   (e) fossefallet faar tre gjensidig utelukkende kategorier med de seks
//       dobbeltkunngjorte boene som annotasjon, aldri som fjerde kategori.
//
// Klassifisering: kanonisk kaskade (kohort-bransjeklassifikator.mjs) + kanonisk
// femsifret SN2007-kode fra bransjekart-v3_2026-08-30.json. Byggflagg beregnes av
// koden, aldri av kartets flaggkolonner (MAA-FIKSES 9). Utfallsregel: forste
// utfallskunngjoring PAA/ETTER aapningen; ved samme dato vinner innstillingen.
//
// Skriptet ASSERTERER mot talljournalens kanoniske tall og mot de gamle frosne
// filene der de var korrekte, og nekter aa skrive hvis noe avviker.
// PERSONVERN: kun aggregater; ingen orgnr, navn eller bostyrere forlater skriptet.
import { getPool, closePool } from "./db.mjs";
import { readFileSync, writeFileSync } from "node:fs";
import { createHash } from "node:crypto";
import { slaaOpp, erByggF, erByggUtforende } from "./kohort-bransjeklassifikator.mjs";

const ROOT = "./del-1-hovedstudien";
const DATA = `${ROOT}/data`, FIG = `${ROOT}/figurer`;
const KJORT = "2026-08-30";
const FRA = "2023-09-01", TIL = "2024-12-31", C_FRA = "2023-08-24";
const MIN = 10;

const pool = getPool();
const sha = (s) => createHash("sha256").update(s).digest("hex");
const pst = (a, b) => (b ? +(100 * a / b).toFixed(1) : null);
const feil = [];
const ok = (navn, betingelse, detalj) => {
  console.log(`${betingelse ? "OK  " : "FEIL"} ${navn}${detalj ? " — " + detalj : ""}`);
  if (!betingelse) feil.push(navn + (detalj ? ": " + detalj : ""));
};
const skrevet = [];
function skrivCsv(sti, rader, sep = ";") {
  const kol = Object.keys(rader[0]);
  const esc = (v) => v === null || v === undefined ? ""
    : (new RegExp(`[",\\n${sep}]`).test(String(v)) ? '"' + String(v).replace(/"/g, '""') + '"' : String(v));
  const csv = [kol.join(sep), ...rader.map(r => kol.map(k => esc(r[k])).join(sep))].join("\n") + "\n";
  writeFileSync(sti, csv, "utf8");
  skrevet.push({ fil: sti.replace(ROOT + "/", ""), rader: rader.length, sha256: sha(csv) });
  console.log(`skrev ${sti.split("/").pop()} (${rader.length} rader)`);
}
function kvantil(arr, q) {
  if (!arr.length) return null;
  const s = arr.slice().sort((a, b) => a - b);
  const i = (s.length - 1) * q, lo = Math.floor(i), hi = Math.ceil(i);
  return lo === hi ? s[lo] : +(s[lo] + (s[hi] - s[lo]) * (i - lo)).toFixed(1);
}
// Clopper-Pearson (samme numerikk som kohort-20)
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
function cp(k, n) {
  if (!n) return [null, null];
  const lo = k === 0 ? 0 : invIbeta(k, n - k + 1, 0.025);
  const hi = k === n ? 1 : invIbeta(k + 1, n - k, 0.975);
  return [+(100 * lo).toFixed(1), +(100 * hi).toFixed(1)];
}

// v3-kartet: kanonisk femsifret kode per trykt etikett (kun visning/kryssjekk)
const kartV3 = JSON.parse(readFileSync(`${DATA}/bransjekart-v3_${KJORT}.json`, "utf8"));
const v3 = new Map(kartV3.kart.map((r) => [r.etikett.normalize("NFC"), r]));

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
       (ie.dato - k.aapning) as d_innst
from kohort k
left join attr a         on a.orgnr = k.orgnr
left join innst_etter ie on ie.orgnr = k.orgnr
left join avsl_etter ae  on ae.orgnr = k.orgnr
`;

try {
  await pool.query("set statement_timeout = '900s'");
  const t0 = Date.now();
  const alle = (await pool.query(SQL, [C_FRA])).rows;
  console.log(`hentet ${alle.length} aapninger fra ${C_FRA} paa ${((Date.now() - t0) / 1000).toFixed(1)} s`);

  for (const r of alle) {
    r.linje1 = (r.bransje || "").split("\n")[0].trim();
    const t = slaaOpp(r.bransje);
    r.kaskadekode = t.kode;
    const v = v3.get((r.bransje || "").normalize("NFC")) || v3.get(r.linje1.normalize("NFC"));
    r.nace = (v && v.kanonisk_sn2007) || t.kode;   // kanonisk femsifret der kartet har den
    r.naceNavn = (v && v.kanonisk_navn) || null;
    r.byggU = erByggUtforende(r.kaskadekode);       // flagg av KASKADENS kode (kanonisk)
    r.byggF = erByggF(r.kaskadekode);
    r.innstilt = !!r.innstilling;
    r.ikkeInnstilt = !r.innstilling;                // avsluttet-uten-innstilling + fortsatt aapen
    r.kunAvsluttet = !r.innstilling && !!r.avslutning;
    r.aapen = !r.innstilling && !r.avslutning;
    r.begge = !!r.innstilling && !!r.avslutning;
  }
  const koh = alle.filter(r => r.aapning >= FRA && r.aapning <= TIL);
  const cVindu = alle.filter(r => r.aapning >= C_FRA && r.aapning <= TIL);

  // ------------------------------------------------ kanoniske assertions (talljournalen A/B)
  const n = (s) => s.length, ni = (s) => s.filter(r => r.innstilt).length;
  const bygg = koh.filter(r => r.byggU), ovr = koh.filter(r => !r.byggU);
  const F = koh.filter(r => r.byggF), ukl = koh.filter(r => !r.kaskadekode);
  ok("A1 kohort = 5165", n(koh) === 5165, String(n(koh)));
  ok("A2 innstilt = 3897", ni(koh) === 3897, String(ni(koh)));
  ok("A3 kun avsluttet = 917", koh.filter(r => r.kunAvsluttet).length === 917);
  ok("A4 fortsatt aapne = 351", koh.filter(r => r.aapen).length === 351);
  ok("A5 begge = 6", koh.filter(r => r.begge).length === 6);
  ok("B1/B2 bygg utforende 1280/911", n(bygg) === 1280 && ni(bygg) === 911, `${n(bygg)}/${ni(bygg)}`);
  ok("B3 bygg avsluttet/aapne 258/111",
     bygg.filter(r => r.kunAvsluttet).length === 258 && bygg.filter(r => r.aapen).length === 111);
  ok("B4 omraade F 1411/1016", n(F) === 1411 && ni(F) === 1016, `${n(F)}/${ni(F)}`);
  ok("B6 ovrige 3885/2986", n(ovr) === 3885 && ni(ovr) === 2986, `${n(ovr)}/${ni(ovr)}`);
  ok("B10 uklassifiserbar 155/143", n(ukl) === 155 && ni(ukl) === 143, `${n(ukl)}/${ni(ukl)}`);
  const eiend = koh.filter(r => r.kaskadekode && /^41\.1/.test(r.kaskadekode));
  ok("B5 eiendomsutvikling 131/105", n(eiend) === 131 && ni(eiend) === 105, `${n(eiend)}/${ni(eiend)}`);

  // C-vinduet (byggfagtabellen i kap. 7)
  const fagC = (navn) => {
    const d = cVindu.filter(r => r.linje1 === navn);
    return [d.length, ni(d)];
  };
  ok("C Oppforing 600/415", fagC("Oppføring av bygninger").join("/") === "600/415", fagC("Oppføring av bygninger").join("/"));
  ok("C Snekker 178/138", fagC("Snekkerarbeid").join("/") === "178/138", fagC("Snekkerarbeid").join("/"));
  ok("C Grunnarbeid 107/81", fagC("Grunnarbeid").join("/") === "107/81");
  ok("C Maler 63/47", fagC("Malerarbeid").join("/") === "63/47");
  ok("C Elektrisk 60/43", fagC("Elektrisk installasjonsarbeid").join("/") === "60/43");
  ok("C Rorlegger 83/55", fagC("Rørleggerarbeid").join("/") === "83/55");
  // kanonisk vindu (kohort-per-bransje): revisors kanoniske Oppforing 593/409
  const oppK = koh.filter(r => r.linje1 === "Oppføring av bygninger");
  ok("kanonisk vindu Oppforing 593/409", `${n(oppK)}/${ni(oppK)}` === "593/409", `${n(oppK)}/${ni(oppK)}`);
  const snekK = koh.filter(r => r.linje1 === "Snekkerarbeid");
  console.log(`info: kanonisk vindu Snekkerarbeid = ${n(snekK)}/${ni(snekK)} (manus sier 175/135)`);

  // ------------------------------------------------ 1 PUBLISERBAR per bransje (kanonisk vindu)
  // Gruppering paa forstelinje-etiketten; kanonisk femsifret kode fra v3-kartet.
  const perB = new Map();
  for (const r of koh) {
    const key = r.kaskadekode ? r.linje1 : "(uklassifiserbar næringsangivelse)";
    const e = perB.get(key) || { etikett: key, nace: r.kaskadekode ? (r.nace || "") : "",
                                 byggU: r.kaskadekode ? r.byggU : null, byggF: r.kaskadekode ? r.byggF : null,
                                 n: 0, i: 0 };
    e.n++; if (r.innstilt) e.i++;
    perB.set(key, e);
  }
  const bRad = (e) => {
    const [lo, hi] = cp(e.i, e.n);
    return { bransje_etikett: e.etikett, nace_sn2007: e.nace,
             er_bygg_utforende: e.byggU === null ? "" : (e.byggU ? 1 : 0),
             er_bygg_omraade_F: e.byggF === null ? "" : (e.byggF ? 1 : 0),
             aapninger: e.n, innstilt: e.i, ikke_innstilt: e.n - e.i,
             innstilt_pst: pst(e.i, e.n), ki95_lav: lo, ki95_hoy: hi };
  };
  const alleB = [...perB.values()].sort((a, b) => b.n - a.n);
  const beholdB = alleB.filter(e => e.i >= MIN && (e.n - e.i) >= MIN);
  const tynnB = alleB.filter(e => !(e.i >= MIN && (e.n - e.i) >= MIN));
  const restB = { etikett: `(${tynnB.length} etiketter med færre enn ${MIN} bo i en utfallskolonne, slått sammen)`,
                  nace: "", byggU: null, byggF: null,
                  n: tynnB.reduce((a, e) => a + e.n, 0), i: tynnB.reduce((a, e) => a + e.i, 0) };
  const perBransjeRader = [...beholdB.map(bRad), bRad(restB)];
  ok("per-bransje: alle celler >= 10", perBransjeRader.every(r => r.innstilt >= MIN && r.ikke_innstilt >= MIN));
  ok("per-bransje: summerer til kohorten",
     perBransjeRader.reduce((a, r) => a + r.aapninger, 0) === 5165 &&
     perBransjeRader.reduce((a, r) => a + r.innstilt, 0) === 3897);
  const uklRad = perBransjeRader.find(r => r.bransje_etikett.startsWith("(uklassifiserbar"));
  ok("per-bransje: 155-botta publisert samlet", !!uklRad && uklRad.aapninger === 155 && uklRad.innstilt === 143);
  const oppRad = perBransjeRader.find(r => r.bransje_etikett === "Oppføring av bygninger");
  ok("per-bransje: Oppforing 593/409 med kanonisk kode", !!oppRad && oppRad.aapninger === 593 &&
     oppRad.innstilt === 409 && oppRad.nace_sn2007 === "41.200", oppRad && `${oppRad.aapninger}/${oppRad.innstilt}/${oppRad.nace_sn2007}`);
  if (!feil.length) {
    skrivCsv(`${DATA}/PUBLISERBAR-per-bransje-${KJORT}.csv`, perBransjeRader);
    skrivCsv(`${DATA}/kohort-per-bransje-${KJORT}.csv`, perBransjeRader);
  }

  // ------------------------------------------------ 2 PUBLISERBAR per tingrett (n >= 100)
  const perR = new Map();
  for (const r of koh) {
    const navn = r.tingrett || "(uoppgitt)";
    const e = perR.get(navn) || { tingrett: navn, saker: 0, i: 0, bygg: 0, dager: [] };
    e.saker++; if (r.innstilt) { e.i++; e.dager.push(r.d_innst); }
    if (r.byggU) e.bygg++;
    perR.set(navn, e);
  }
  const kretser = [...perR.values()].sort((a, b) => b.saker - a.saker);
  const store = kretser.filter(e => e.saker >= 100);
  ok("tingrett: 16 kretser med n >= 100", store.length === 16, String(store.length));
  ok("tingrett: 4698 saker i de 16", store.reduce((a, e) => a + e.saker, 0) === 4698,
     String(store.reduce((a, e) => a + e.saker, 0)));
  // kontinuitet mot den gamle (verifiserte) fila for de 16 store kretsene
  const gammelRett = readFileSync(`${DATA}/PUBLISERBAR-per-tingrett-${KJORT}.csv`, "utf8")
    .trim().split("\n").slice(1).map(l => {
      const c = l.match(/("[^"]*"|[^;]+)/g).map(x => x.replace(/^"|"$/g, ""));
      return { tingrett: c[0], saker: +c[1], innstilt: +c[2] };
    });
  for (const e of store) {
    const g = gammelRett.find(x => x.tingrett === e.tingrett);
    ok(`tingrett ${e.tingrett}: uendrede tall`, !!g && g.saker === e.saker && g.innstilt === e.i,
       g ? `${e.saker}/${e.i} mot ${g.saker}/${g.innstilt}` : "mangler i gammel fil");
  }
  const rettRader = store.map(e => {
    const [lo, hi] = cp(e.i, e.saker);
    return { tingrett: e.tingrett, saker: e.saker, innstilt: e.i, ikke_innstilt: e.saker - e.i,
             innstilt_pst: pst(e.i, e.saker), ki95_lav: lo, ki95_hoy: hi,
             byggandel_pst: pst(e.bygg, e.saker),
             median_dager_til_innstilling: kvantil(e.dager, 0.5),
             kvartil1_dager: kvantil(e.dager, 0.25), kvartil3_dager: kvantil(e.dager, 0.75) };
  });
  ok("tingrett: alle celler >= 22", rettRader.every(r => r.innstilt >= 22 && r.ikke_innstilt >= 22));
  if (!feil.length) {
    skrivCsv(`${DATA}/PUBLISERBAR-per-tingrett-${KJORT}.csv`, rettRader);
    skrivCsv(`${DATA}/kohort-per-tingrett-${KJORT}.csv`, rettRader);
  }

  // ------------------------------------------------ 3 bygg per tingrett (uten Nord-Troms og Senja)
  const byggRett = [];
  for (const e of store) {
    const d = koh.filter(x => (x.tingrett || "(uoppgitt)") === e.tingrett);
    const b = d.filter(x => x.byggU), o = d.filter(x => !x.byggU);
    const bi = ni(b), oi = ni(o);
    const rad = { tingrett: e.tingrett,
      bygg_saker: b.length, bygg_innstilt: bi, bygg_ikke_innstilt: b.length - bi,
      bygg_innstilt_pst: pst(bi, b.length),
      ovrige_saker: o.length, ovrige_innstilt: oi, ovrige_ikke_innstilt: o.length - oi,
      ovrige_innstilt_pst: pst(oi, o.length),
      bygg_median_dager: kvantil(b.filter(x => x.innstilt).map(x => x.d_innst), 0.5),
      ovrige_median_dager: kvantil(o.filter(x => x.innstilt).map(x => x.d_innst), 0.5) };
    const alleCellerOk = [rad.bygg_innstilt, rad.bygg_ikke_innstilt, rad.ovrige_innstilt, rad.ovrige_ikke_innstilt]
      .every(v => v >= MIN);
    if (alleCellerOk) byggRett.push(rad);
    else console.log(`strøket byggsplitt (celle < ${MIN}): ${rad.tingrett} (bygg ${rad.bygg_innstilt}/${rad.bygg_ikke_innstilt})`);
  }
  ok("bygg-per-tingrett: Nord-Troms og Senja stroket, 15 rader igjen",
     byggRett.length === 15 && !byggRett.some(r => r.tingrett === "NORD-TROMS OG SENJA TINGRETT"),
     String(byggRett.length));
  if (!feil.length) skrivCsv(`${DATA}/PUBLISERBAR-bygg-per-tingrett-${KJORT}.csv`, byggRett);

  // ------------------------------------------------ 4 F1 byggfag (C-vinduet, kanonisk kode)
  const perFag = new Map();
  for (const r of cVindu) {
    const v = v3.get((r.bransje || "").normalize("NFC")) || v3.get(r.linje1.normalize("NFC"));
    if (!v || !v.kanonisk_sn2007) continue;
    const kode = v.kanonisk_sn2007;
    if (!erByggF(kode)) continue;
    const kjerne = erByggUtforende(kode); // av koden, aldri av kartets flagg
    const key = kode + "|" + v.kanonisk_navn + "|" + kjerne;
    const e = perFag.get(key) || { kode, navn: v.kanonisk_navn, kjerne, n: 0, i: 0 };
    e.n++; if (r.innstilt) e.i++;
    perFag.set(key, e);
  }
  const FIGURFAG = new Set(["43.320", "43.120", "43.341", "43.210", "41.200", "43.221"]);
  const fagAlle = [...perFag.values()].sort((a, b) => pst(b.i, b.n) - pst(a.i, a.n));
  const fagBehold = fagAlle.filter(e => e.i >= MIN && (e.n - e.i) >= MIN);
  const fagTynn = fagAlle.filter(e => !(e.i >= MIN && (e.n - e.i) >= MIN));
  const fagRest = { kode: "(samlet)", kjerne: "",
    navn: `Byggnæringer med færre enn ${MIN} bo i en utfallskolonne (${fagTynn.length} næringer, slått sammen)`,
    n: fagTynn.reduce((a, e) => a + e.n, 0), i: fagTynn.reduce((a, e) => a + e.i, 0) };
  const fagRad = (e) => {
    const [lo, hi] = cp(e.i, e.n);
    return { nace_sn2007: e.kode, naering: e.navn, er_byggfag_kjerne: e.kjerne === "" ? "" : e.kjerne,
             vises_i_figur3: FIGURFAG.has(e.kode), n_apnede_bo: e.n,
             innstilt: e.i, ikke_innstilt: e.n - e.i,
             innstilt_pst: pst(e.i, e.n), ki95_lav: lo, ki95_hoy: hi };
  };
  const f1Rader = [...fagBehold.map(fagRad), fagRad(fagRest)];
  ok("F1: alle celler >= 10", f1Rader.every(r => r.innstilt >= MIN && r.ikke_innstilt >= MIN));
  ok("F1: Oppforing 600/415", f1Rader.some(r => r.nace_sn2007 === "41.200" && r.n_apnede_bo === 600 && r.innstilt === 415));
  ok("F1: Snekker 178/138", f1Rader.some(r => r.nace_sn2007 === "43.320" && r.n_apnede_bo === 178 && r.innstilt === 138));
  ok("F1: de seks figurfagene er med", f1Rader.filter(r => r.vises_i_figur3 === true).length === 6);
  if (!feil.length) skrivCsv(`${FIG}/F1-byggfag-innstillingsandel_${KJORT}.csv`, f1Rader, ",");

  // ------------------------------------------------ 5 fossefall (tre gjensidig utelukkende utfall)
  const gr = [["ALLE næringer", koh], ["BYGG (utførende)", bygg], ["ØVRIGE næringer", ovr]];
  const per1000 = (a, b) => Math.round(1000 * a / b);
  const fossefall = gr.map(([navn, s]) => {
    const i = ni(s), a = s.filter(r => r.kunAvsluttet).length, o = s.filter(r => r.aapen).length;
    const b6 = s.filter(r => r.begge).length;
    return { gruppe: navn, bo: s.length,
             innstilt: i, kun_avsluttet: a, fortsatt_apne: o,
             per1000_innstilt: per1000(i, s.length),
             per1000_kun_avsluttet: per1000(a, s.length),
             per1000_fortsatt_apne: per1000(o, s.length),
             herav_begge_kunngjoringer_annotasjon: b6 };
  });
  const fAlle = fossefall[0], fBygg = fossefall[1], fOvr = fossefall[2];
  ok("fossefall ALLE 3897/917/351, per1000 755/178/68",
     fAlle.innstilt === 3897 && fAlle.kun_avsluttet === 917 && fAlle.fortsatt_apne === 351 &&
     fAlle.per1000_innstilt === 755 && fAlle.per1000_kun_avsluttet === 178 && fAlle.per1000_fortsatt_apne === 68,
     JSON.stringify(fAlle));
  ok("fossefall BYGG 911/258/111", fBygg.innstilt === 911 && fBygg.kun_avsluttet === 258 && fBygg.fortsatt_apne === 111);
  ok("fossefall OVRIGE 2986/659/240", fOvr.innstilt === 2986 && fOvr.kun_avsluttet === 659 && fOvr.fortsatt_apne === 240);
  ok("fossefall: annotasjonen inngaar ikke i summen",
     fossefall.every(f => f.innstilt + f.kun_avsluttet + f.fortsatt_apne === f.bo));
  if (!feil.length) skrivCsv(`${FIG}/fossefall-per-1000-bo-${KJORT}.csv`, fossefall);

  // ------------------------------------------------ 6 kvartal x naering-aggregat (to utfallskolonner)
  const kvartalAv = (d) => d.slice(0, 4) + "K" + (Math.floor((+d.slice(5, 7) - 1) / 3) + 1);
  const perKN = new Map();
  for (const r of koh) {
    const kv = kvartalAv(r.aapning);
    const kode = r.kaskadekode ? (r.nace || r.kaskadekode) : "(uklassifiserbar)";
    const navn = r.kaskadekode ? (r.naceNavn || "") : "(uklassifiserbar næringsangivelse)";
    const key = kv + "|" + kode;
    const e = perKN.get(key) || { kv, kode, navn, byggF: r.kaskadekode ? r.byggF : "", byggU: r.kaskadekode ? r.byggU : "", n: 0, i: 0 };
    e.n++; if (r.innstilt) e.i++;
    perKN.set(key, e);
  }
  const knAlle = [...perKN.values()];
  const knBehold = knAlle.filter(e => e.i >= MIN && (e.n - e.i) >= MIN);
  const kvartaler = [...new Set(knAlle.map(e => e.kv))].sort();
  const knRader = [];
  for (const kv of kvartaler) {
    for (const e of knBehold.filter(e => e.kv === kv).sort((a, b) => b.n - a.n)) {
      knRader.push({ aapning_kvartal: kv, kanonisk_sn2007: e.kode, kanonisk_navn: e.navn,
        er_bygg_omraade_F: e.byggF === "" ? "" : (e.byggF ? 1 : 0),
        er_bygg_utforende: e.byggU === "" ? "" : (e.byggU ? 1 : 0),
        antall_bo: e.n, innstilt: e.i, ikke_innstilt: e.n - e.i });
    }
    const tynn = knAlle.filter(e => e.kv === kv && !(e.i >= MIN && (e.n - e.i) >= MIN));
    const tn = tynn.reduce((a, e) => a + e.n, 0), ti = tynn.reduce((a, e) => a + e.i, 0);
    knRader.push({ aapning_kvartal: kv,
      kanonisk_sn2007: "(restrad)",
      kanonisk_navn: `Næringer med færre enn ${MIN} bo i en utfallskolonne i kvartalet (${tynn.length} næringer, slått sammen)`,
      er_bygg_omraade_F: "", er_bygg_utforende: "",
      antall_bo: tn, innstilt: ti, ikke_innstilt: tn - ti });
  }
  ok("kvartalsaggregat: alle celler >= 10", knRader.every(r => r.innstilt >= MIN && r.ikke_innstilt >= MIN));
  ok("kvartalsaggregat: summerer til kohorten",
     knRader.reduce((a, r) => a + r.antall_bo, 0) === 5165 && knRader.reduce((a, r) => a + r.innstilt, 0) === 3897);
  if (!feil.length) skrivCsv(`${DATA}/bransje-kohortaggregat-A_${KJORT}.csv`, knRader, ",");

  // ------------------------------------------------ kvittering
  if (feil.length) {
    console.error("\nREASSEMBLERING NEKTET — " + feil.length + " kontroller feilet:\n" + feil.join("\n"));
    process.exitCode = 1;
  } else {
    const kvittering = {
      operasjon: "sluttredaksjonens reassemblering av publiseringsfilene (talljournalens MAA-FIKSES 2, revisjonens kritiske defekt)",
      kjoredato: KJORT, kohortvindu: { fra: FRA, til: TIL }, c_vindu: { fra: C_FRA, til: TIL },
      utfallsregel: "forste utfallskunngjoring paa/etter aapningen; ved samme dato vinner innstillingen",
      minstecelle: MIN, sporring_sha256: sha(SQL), filer: skrevet,
    };
    writeFileSync(`${DATA}/sluttred-reassemblering-${KJORT}.json`, JSON.stringify(kvittering, null, 1), "utf8");
    console.log("\nALLE KONTROLLER OK — filer skrevet:\n" + skrevet.map(f => ` ${f.fil} sha256=${f.sha256}`).join("\n"));
  }
} catch (e) {
  console.error("FEIL:", e.message, e.stack);
  process.exitCode = 1;
} finally {
  await closePool();
}
