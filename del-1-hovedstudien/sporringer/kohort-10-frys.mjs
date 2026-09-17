// kohort — FRYS AV KOHORTEN (READ-ONLY, kun SELECT).
//
// REFROSSET 2026-08-30 (sluttredaksjonen, talljournalens MAA-FIKSES 1): bransje
// klassifiseres naa med den KANONISKE kaskadeklassifikatoren (kohort-bransjeklassifikator.mjs,
// samme som kohort-20 og kontrolloren) og kryssjekkes mot det frosne kartet
// bransjekart-v3_2026-08-30.json (kanonisk femsifret SN2007-kode per etikett).
// Det stale oppslaget mot bransjekart-v2.json er fjernet — det mistet 10 bo
// («Blikkenslagerarbeid paa tak») og ga en for stor uklassifisert-botte (226 mot 155).
// NB: v3-kartets flagg er_bygg_kjerne=true for SN2025-etiketten «Utvikling og salg av
// byggeprosjekter» er i strid med kjernedefinisjonen (MAA-FIKSES 9) og brukes IKKE;
// byggflaggene beregnes alltid av koden (erByggF/erByggUtforende). Null effekt paa
// kohorten, som ligger foer sommen 2025-09-01.
//
// Kohort: distinkte selskaper med sin FORSTE «Konkurs - åpning» i 2023-09-01..2024-12-31.
// To former beregnes og sammenlignes:
//   A  global-forste: min(dato) over ALLE aapningsrader, filtrert til vinduet   (kanonisk)
//   B  vindu-forste : selskaper med minst en aapningsrad i vinduet              (kontroll)
//
// Utfall leses direkte fra kunngjoringene — ALDRI fra company_intel.livslop (L16:
// livslop.utfall og tvang_dato er forurenset av varselmasken; feilen eies av en annen lane).
// Alle tellinger er count(distinct orgnr) (L8/L14). Utfylling maales med
// nullif(trim(...),'') (L5). Datoer hentes som TEKST — pg-driveren forskyver date til
// lokal tid og flytter dagen ett dogn i JSON.
//
// PERSONVERN: ingen orgnr, ingen selskapsnavn, ingen bostyrere forlater dette skriptet.
// Kohorten fryses som (a) et aggregatkube og (b) et FINGERAVTRYKK — sha256 over den
// sorterte orgnr-listen, beregnet inne i databasen. Fingeravtrykket beviser at en senere
// kjoring traff nøyaktig samme kohort, uten å rope ut hvilke selskaper det var.
import { getPool, closePool } from "./db.mjs";
import { writeFileSync, readFileSync } from "node:fs";
import { createHash } from "node:crypto";

const DATA = "./data";
const FIG = "./figurer";
const KJORT = new Date().toISOString().slice(0, 10);
const VINDU_FRA = "2023-09-01";
const VINDU_TIL = "2024-12-31";

const pool = getPool();
const out = (l, r) => { console.log("\n=== " + l + " ==="); console.log(JSON.stringify(r, null, 1)); };
const sha = (s) => createHash("sha256").update(s).digest("hex");

function skrivCsv(sti, rader) {
  if (!rader.length) { writeFileSync(sti, "", "utf8"); return ""; }
  const kol = Object.keys(rader[0]);
  const esc = (v) => {
    if (v === null || v === undefined) return "";
    const s = String(v);
    return /[",\n;]/.test(s) ? '"' + s.replace(/"/g, '""') + '"' : s;
  };
  const csv = [kol.join(";"), ...rader.map(r => kol.map(k => esc(r[k])).join(";"))].join("\n") + "\n";
  writeFileSync(sti, csv, "utf8");
  return sha(csv);
}

// ---------------------------------------------------------------- bransjeordbok
// Kanonisk klassifisering: kaskaden mot SSB Klass-kodelistene (samme modul som
// kohort-20 og kontrolloren). v3-kartet lastes i tillegg for (a) kanonisk femsifret
// SN2007-kode per etikett og (b) kryssjekk av byggflaggene (skal vaere 0 uenige).
import { slaaOpp, erByggF as erByggFKanonisk, erByggUtforende } from "./kohort-bransjeklassifikator.mjs";
const KARTFIL = "bransjekart-v3_2026-08-30.json";
const kartV3 = JSON.parse(readFileSync(`${DATA}/${KARTFIL}`, "utf8"));
const v3PerEtikett = new Map(kartV3.kart.map((r) => [r.etikett.normalize("NFC"), r]));
function slaaOppKode(etikett) {
  if (!etikett) return null;
  const t = slaaOpp(etikett); // forstelinje-reparasjonen ligger inne i kaskaden
  if (!t.kode) return null;
  // kanonisk femsifret kode fra v3-kartet der den finnes; ellers kaskadens kode
  const v3 = v3PerEtikett.get(etikett.normalize("NFC"));
  const kode = v3?.kanonisk_sn2007 || t.kode;
  return { kode, navn: v3?.kanonisk_navn || null, kaskadekode: t.kode };
}
// To bygg-definisjoner, fordi de gir ulike tall og forskjellen maa staa i teksten.
// Flaggene beregnes ALLTID av koden — aldri av v3-kartets flaggkolonner (MAA-FIKSES 9).
const erByggF = (k) => erByggFKanonisk(k);
const erByggUtf = (k) => erByggUtforende(k);

const SQL_KOHORT = `
with aapning as materialized (
  select orgnr,
         min(dato)                                                as forste_aapning_global,
         min(dato) filter (where dato between $1::date and $2::date) as forste_aapning_i_vindu,
         count(*)                                                 as aapningsrader
  from kunngjoring.insolvens
  where type = 'Konkurs - åpning'
  group by orgnr
),
kohort as materialized (
  select orgnr, forste_aapning_global as aapning, forste_aapning_i_vindu, aapningsrader
  from aapning
  where forste_aapning_global between $1::date and $2::date
),
attr as materialized (
  select i.orgnr,
         nullif(trim(i.bransje),'')  as bransje,
         nullif(trim(i.tingrett),'') as tingrett,
         nullif(trim(i.saksnr),'')   as saksnr,
         i.fristdag
  from kunngjoring.insolvens i
  join kohort k on k.orgnr = i.orgnr and i.dato = k.aapning
  where i.type = 'Konkurs - åpning'
),
innstilling as materialized (
  select orgnr, min(dato) as dato, count(*) as rader
  from kunngjoring.insolvens
  where type = 'Konkurs - innstilling av bobehandlingen'
  group by orgnr
),
avslutning as materialized (
  select orgnr, min(dato) as dato, count(*) as rader
  from kunngjoring.insolvens
  where type = 'Konkurs - avslutning av bobehandlingen'
  group by orgnr
),
fortsettelse as materialized (
  select orgnr, min(dato) as dato from kunngjoring.insolvens
  where type = 'Fortsettelse av bobehandling' group by orgnr
)
select k.orgnr,
       to_char(k.aapning,'YYYY-MM-DD')                as aapning,
       to_char(k.forste_aapning_i_vindu,'YYYY-MM-DD') as aapning_i_vindu,
       k.aapningsrader,
       a.bransje, a.tingrett, a.saksnr,
       to_char(i.dato,'YYYY-MM-DD') as innstilling,
       to_char(v.dato,'YYYY-MM-DD') as avslutning,
       to_char(f.dato,'YYYY-MM-DD') as fortsettelse,
       (i.dato - k.aapning) as dager_til_innstilling,
       (v.dato - k.aapning) as dager_til_avslutning
from kohort k
left join attr a         on a.orgnr = k.orgnr
left join innstilling i  on i.orgnr = k.orgnr
left join avslutning v   on v.orgnr = k.orgnr
left join fortsettelse f on f.orgnr = k.orgnr
`;

try {
  await pool.query("set statement_timeout = '900s'");

  const t0 = Date.now();
  const rader = (await pool.query(SQL_KOHORT, [VINDU_FRA, VINDU_TIL])).rows;
  console.log(`kohortspørringen: ${rader.length} rader på ${((Date.now()-t0)/1000).toFixed(1)} s`);

  // ---------------------------------------------------------------- fingeravtrykk
  const fp = (await pool.query(`
    with aapning as materialized (
      select orgnr, min(dato) as f from kunngjoring.insolvens
      where type='Konkurs - åpning' group by orgnr
    )
    select encode(sha256(convert_to(string_agg(orgnr, ',' order by orgnr), 'UTF8')), 'hex') as fingeravtrykk,
           count(*) as n
    from aapning where f between $1::date and $2::date
  `, [VINDU_FRA, VINDU_TIL])).rows[0];
  out("kohortens fingeravtrykk (sha256 over sortert orgnr-liste, beregnet i databasen)", fp);

  // ---------------------------------------------------------------- form A vs form B
  const formB = (await pool.query(`
    select count(distinct orgnr) as n from kunngjoring.insolvens
    where type='Konkurs - åpning' and dato between $1::date and $2::date
  `, [VINDU_FRA, VINDU_TIL])).rows[0];
  out("form A (global-forste i vindu) vs form B (minst en aapning i vindu)", {
    form_A_global_forste: rader.length,
    form_B_vindu_forste: Number(formB.n),
    differanse: Number(formB.n) - rader.length,
  });

  // ---------------------------------------------------------------- klassifisering
  let v3Uenige = 0;
  for (const r of rader) {
    const treff = slaaOppKode(r.bransje);
    r.nace = treff ? treff.kode : null;           // kanonisk femsifret (visning)
    r.nace_navn = treff ? treff.navn : null;
    const flaggkode = treff ? treff.kaskadekode : null; // kaskadens kode (kanonisk flaggrunnlag)
    r.bygg_F = erByggF(flaggkode);
    r.bygg_utforende = erByggUtf(flaggkode);
    // kryssjekk mot v3-kartets kanoniske kode: byggflagg av kode skal vaere identiske
    if (treff && treff.kode !== flaggkode &&
        (erByggF(treff.kode) !== r.bygg_F || erByggUtf(treff.kode) !== r.bygg_utforende)) v3Uenige++;
    r.utfall = r.innstilling && r.avslutning ? "begge"
             : r.innstilling ? "innstilt"
             : r.avslutning ? "avsluttet" : "fortsatt_apen";
  }
  console.log(`byggflagg-uenighet kaskade vs v3-kanonisk kode: ${v3Uenige} selskaper (skal vaere 0)`);

  const uklassifisert = rader.filter(r => !r.nace);
  out("bransje-utfylling og NACE-oppslag", {
    kohort: rader.length,
    med_bransje_etikett: rader.filter(r => r.bransje).length,
    uten_bransje_etikett: rader.filter(r => !r.bransje).length,
    nace_oppslag_traff: rader.length - uklassifisert.length,
    nace_oppslag_bommet: uklassifisert.length,
    bommede_etiketter: [...new Set(uklassifisert.map(r => r.bransje))].slice(0, 40),
  });

  // ---------------------------------------------------------------- hovedtall
  const tell = (pred) => rader.filter(pred).length;
  const andel = (a, b) => b ? +(100 * a / b).toFixed(1) : null;
  const harInnst = (r) => !!r.innstilling, harAvsl = (r) => !!r.avslutning;

  function hovedtall(navn, delmengde) {
    const n = delmengde.length;
    const i = delmengde.filter(harInnst).length;
    const a = delmengde.filter(harAvsl).length;
    const b = delmengde.filter(r => harInnst(r) && harAvsl(r)).length;
    const o = delmengde.filter(r => !harInnst(r) && !harAvsl(r)).length;
    return { gruppe: navn, aapninger: n,
             innstilt: i, innstilt_pst: andel(i, n),
             avsluttet: a, avsluttet_pst: andel(a, n),
             begge: b,
             fortsatt_apne: o, fortsatt_apne_pst: andel(o, n),
             kun_innstilt: i - b, kun_avsluttet: a - b };
  }

  const hoved = [
    hovedtall("ALLE", rader),
    hovedtall("BYGG (NACE F, 41-43)", rader.filter(r => r.bygg_F)),
    hovedtall("BYGG utforende (41.2+42+43)", rader.filter(r => r.bygg_utforende)),
    hovedtall("EIENDOMSUTVIKLING (41.1)", rader.filter(r => r.nace && /^41\.1/.test(r.nace))),
    hovedtall("OVRIGE (ikke NACE F)", rader.filter(r => !r.bygg_F)),
    hovedtall("OVRIGE (ikke utforende bygg)", rader.filter(r => !r.bygg_utforende)),
    hovedtall("UKLASSIFISERT", uklassifisert),
  ];
  out("HOVEDTALL", hoved);

  // ------------------------------------------ kryssjekk mot talljournalens kanoniske tall
  const forventet = { kohort: 5165, innstilt: 3897, avsluttet: 923, kun_avsluttet: 917,
                      apne: 351, begge: 6,
                      byggU_aapninger: 1280, byggU_innstilt: 911,
                      byggF_aapninger: 1411, byggF_innstilt: 1016,
                      uklassifisert: 155, uklassifisert_innstilt: 143 };
  const observert = { kohort: hoved[0].aapninger, innstilt: hoved[0].innstilt,
                      avsluttet: hoved[0].avsluttet, kun_avsluttet: hoved[0].kun_avsluttet,
                      apne: hoved[0].fortsatt_apne, begge: hoved[0].begge,
                      byggU_aapninger: hoved[2].aapninger, byggU_innstilt: hoved[2].innstilt,
                      byggF_aapninger: hoved[1].aapninger, byggF_innstilt: hoved[1].innstilt,
                      uklassifisert: hoved[6].aapninger, uklassifisert_innstilt: hoved[6].innstilt };
  const avvik = Object.keys(forventet).filter((k) => forventet[k] !== observert[k]);
  out("kryssjekk mot talljournalens kanoniske tall (A- og B-serien)", { forventet, observert, avvik });
  if (avvik.length) throw new Error("KANONISK KRYSSJEKK FEILET: " + avvik.join(", "));

  // ---------------------------------------------------------------- innstilling for aapning?
  const foerAapning = rader.filter(r => r.dager_til_innstilling !== null && r.dager_til_innstilling < 0);
  out("innstillingsdato FOR aapningsdato (skal vaere 0 i denne kohorten)", {
    antall: foerAapning.length,
    eksempler_dager: foerAapning.slice(0, 10).map(r => r.dager_til_innstilling),
  });

  // Arbeidskopi UTEN orgnr/saksnr — personvernregelen: ingen enkeltselskaper i noen fil.
  writeFileSync(DATA + "/_kohort-rader-arbeidskopi.json",
    JSON.stringify(rader.map(({ orgnr, saksnr, ...r }) => r)), "utf8");
  console.log("\n(arbeidskopi uten orgnr/saksnr skrevet — arbeidsfil, aldri publisert)");

  // ---------------------------------------------------------------- aggregatkube (FRYS)
  // Oppdelingen holdes grov nok til at cellene faktisk kan publiseres. En dypere kube
  // (kvartal x etikett x domstol x utfall) gir 3 751 celler hvorav bare 15 naar n >= 10;
  // marginaltabellene i kohort-20 er den brukbare formen. Her: kvartal x byggflagg x utfall.
  const kvartal = (d) => d.slice(0, 4) + "K" + (Math.floor((Number(d.slice(5, 7)) - 1) / 3) + 1);
  const kube = new Map();
  for (const r of rader) {
    const n = [kvartal(r.aapning), r.bygg_F ? "bygg_F_41_43" : "ovrig", r.utfall].join("");
    kube.set(n, (kube.get(n) || 0) + 1);
  }
  const kubeRader = [...kube].map(([k, n]) => {
    const [aapning_kvartal, byggflagg, utfall] = k.split("");
    return { aapning_kvartal, byggflagg, utfall, antall: n };
  }).sort((a, b) => a.aapning_kvartal.localeCompare(b.aapning_kvartal) || b.antall - a.antall)
    .filter(r => r.antall >= 10);   // tynne celler slippes helt - de er ikke publiserbare
  const kubeSha = skrivCsv(`${DATA}/kohort-aggregatkube-${KJORT}.csv`, kubeRader);
  console.log(`
kohort-aggregatkube-${KJORT}.csv: ${kubeRader.length} celler (alle n>=10), sha256=${kubeSha}`);

  // ---------------------------------------------------------------- sammendrag (FRYS)
  const sammendrag = {
    studie: "Tomme bo — kohortfrys og utfall",
    kjoredato: KJORT,
    kohortvindu: { fra: VINDU_FRA, til: VINDU_TIL },
    korpusslutt: (await pool.query("select to_char(max(dato),'YYYY-MM-DD') d from kunngjoring.insolvens")).rows[0].d,
    kohortdefinisjon: "distinkte selskaper hvis GLOBALT forste «Konkurs - åpning» faller i vinduet",
    fingeravtrykk_sha256: fp.fingeravtrykk,
    sporring_sha256: sha(SQL_KOHORT),
    form_A_antall: rader.length,
    form_B_antall: Number(formB.n),
    bransjeklassifisering: {
      metode: "kanonisk kaskade mot SSB Klass-kodelistene (kohort-bransjeklassifikator.mjs), forstelinje ved flerlinjede etiketter",
      kartfil: KARTFIL,
      kartversjon: kartV3.versjon,
      kilde: "SSB Klass klassifikasjon 6, versjon 30 (SN2007) og 3218 (SN2025), korrespondanse 2919, hentet via data.ssb.no/api/klass",
      byggflagg: "beregnet av koden (41.2/42/43 = utforende; 41-43 = omraade F) — aldri av kartets flaggkolonner",
      byggflagg_uenighet_kaskade_vs_v3: v3Uenige,
    },
    hovedtall: hoved,
  };
  const sammendragJson = JSON.stringify(sammendrag, null, 1);
  writeFileSync(`${DATA}/kohort-sammendrag-${KJORT}.json`, sammendragJson, "utf8");
  console.log(`kohort-sammendrag-${KJORT}.json sha256=${sha(sammendragJson)}`);
} catch (e) {
  console.error("FEIL:", e.message, e.stack);
} finally {
  await closePool();
}
