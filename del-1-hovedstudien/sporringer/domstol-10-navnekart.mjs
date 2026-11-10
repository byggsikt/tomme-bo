// LANE 3 — domstol. Steg 10: den frosne navn->rettskrets-tabellen.
//
// Analyseenheten er RETTSKRETSEN SLIK DEN VAR VED KONKURSÅPNINGEN, identifisert
// ved domstolskoden i saksnr og merkelappet med navnet på åpningsraden.
// Tabellen dekker alle vintager i korpuset og gir hver navnevariant en rolle:
//   kohortnavn   = navnet som gjelder i kohortvinduet 2023-09-01..2024-12-31
//   forgjenger   = navn som forsvant med domstolreformen (siste bruk < 2021-07-01)
//   etterfolger  = navn som oppsto med oppsplittingen (første bruk >= 2025-06-01)
//   sideform     = alt annet (stavevarianter, engangsformer)
// Foreldrekretsen for etterfølgerne utledes av SAKENE: åpningskoden på saker som
// senere fikk innstilling under etterfølgernavnet.
// READ-ONLY. Kjøres: node domstol-10-navnekart.mjs
import { writeFileSync, mkdirSync } from "node:fs";
import { createHash } from "node:crypto";
import { getPool, closePool } from "./db.mjs";

const ROOT = "./del-1-hovedstudien";
const KJORT = new Date().toISOString().slice(0, 10);
mkdirSync(`${ROOT}/data`, { recursive: true });

const pool = getPool();
await pool.query("set statement_timeout = '900s'");

const KODE = (c) => `nullif(regexp_replace(coalesce(substring(upper(trim(${c})) from 'KON-+([A-Z0-9]+)'),''),'KJENNELSE.*$',''),'')`;

// 1) alle navn x kode i korpuset
const { rows: par } = await pool.query(`
  select trim(tingrett) as navn, ${KODE("saksnr")} as kode,
         count(*) as rader, count(distinct orgnr) as selskaper,
         to_char(min(dato),'YYYY-MM-DD') as forste, to_char(max(dato),'YYYY-MM-DD') as siste
    from kunngjoring.insolvens
   where nullif(trim(tingrett),'') is not null
   group by 1,2`);

// 2) kohortkretsene (fasit for merkelappen)
const { rows: kohort } = await pool.query(`
  with aapning as materialized (
    select orgnr, min(dato) as aapning_dato from kunngjoring.insolvens
     where type='Konkurs - åpning' group by orgnr),
  kohort as materialized (
    select orgnr, aapning_dato from aapning
     where aapning_dato between date '2023-09-01' and date '2024-12-31')
  select max(nullif(trim(i.tingrett),'')) as navn, max(${KODE("i.saksnr")}) as kode,
         count(*) as saker
    from kohort k join kunngjoring.insolvens i
      on i.orgnr=k.orgnr and i.dato=k.aapning_dato and i.type='Konkurs - åpning'
   group by i.orgnr`);
const kretsAvKode = new Map(), sakerAvKode = new Map();
for (const r of kohort) {
  if (!r.kode) continue;
  kretsAvKode.set(r.kode, r.navn);
  sakerAvKode.set(r.kode, (sakerAvKode.get(r.kode) || 0) + 1);
}

// 3) etterfølgernavn -> foreldrekrets, utledet fra sakene
const { rows: arv } = await pool.query(`
  with aapning as materialized (
    select orgnr, min(dato) as aapning_dato from kunngjoring.insolvens
     where type='Konkurs - åpning' group by orgnr),
  kohort as materialized (
    select orgnr, aapning_dato from aapning
     where aapning_dato between date '2023-09-01' and date '2024-12-31'),
  aap as materialized (
    select k.orgnr, max(nullif(trim(i.tingrett),'')) as a_navn, max(${KODE("i.saksnr")}) as a_kode
      from kohort k join kunngjoring.insolvens i
        on i.orgnr=k.orgnr and i.dato=k.aapning_dato and i.type='Konkurs - åpning' group by 1),
  ut as materialized (
    select k.orgnr, nullif(trim(i.tingrett),'') as u_navn
      from kohort k join kunngjoring.insolvens i on i.orgnr=k.orgnr
     where i.type in ('Konkurs - innstilling av bobehandlingen',
                      'Konkurs - avslutning av bobehandlingen')
       and nullif(trim(i.tingrett),'') is not null)
  select u.u_navn as etterfolger, a.a_navn as forelder_navn, a.a_kode as forelder_kode,
         count(distinct u.orgnr) as saker
    from ut u join aap a using (orgnr)
   where u.u_navn is distinct from a.a_navn
   group by 1,2,3 order by 1, saker desc`);
const arvAv = new Map();
for (const r of arv) {
  if (!arvAv.has(r.etterfolger)) arvAv.set(r.etterfolger, []);
  arvAv.get(r.etterfolger).push(`${r.forelder_navn} [${r.forelder_kode}] ${r.saker}`);
}

// 4) bygg tabellen
// Kunngjøringene bruker bare det nordsamiske navnet på én domstol; norsk navn
// bekreftet hos Norges domstoler og settes inn så publiserte tabeller er lesbare.
const NORSK_NAVN = new Map([
  ["SIS-JA NUORTA-FINNMÁRKKU DIGGEGODDI", "Indre og Østre Finnmark tingrett"],
]);
const REFORM = "2021-07-01", SPLITT = "2025-06-01";
const rader = par.map((p) => {
  const iKohort = kretsAvKode.has(p.kode) && kretsAvKode.get(p.kode) === p.navn;
  let rolle;
  if (iKohort) rolle = "kohortnavn";
  else if (p.siste < REFORM) rolle = "forgjenger";
  else if (p.forste >= SPLITT) rolle = "etterfolger";
  else rolle = "sideform";
  return {
    navn: p.navn, norsk_navn: NORSK_NAVN.get(p.navn) || "", kode: p.kode || "", rolle,
    krets_kohort: kretsAvKode.get(p.kode) || "",
    krets_kode: kretsAvKode.has(p.kode) ? p.kode : "",
    kohortsaker: kretsAvKode.has(p.kode) ? sakerAvKode.get(p.kode) : "",
    arvet_fra: (arvAv.get(p.navn) || []).join(" ; "),
    rader: p.rader, selskaper: p.selskaper, forste: p.forste, siste: p.siste,
  };
}).sort((a, b) => (a.krets_kohort || "ÆØÅ").localeCompare(b.krets_kohort, "nb")
                || a.navn.localeCompare(b.navn, "nb") || a.forste.localeCompare(b.forste));

const cols = ["navn", "norsk_navn", "kode", "rolle", "krets_kohort", "krets_kode", "kohortsaker",
              "arvet_fra", "rader", "selskaper", "forste", "siste"];
const txt =
`# Byggsikt — Tomme bo, lane 3 (domstol). NAVN -> RETTSKRETS. Kjørt ${KJORT}.
# Kilde: offentlig tilgjengelige registerkunngjøringer om konkursbehandling.
# Analyseenhet: rettskretsen slik den var ved konkursåpningen, identifisert ved
# domstolskoden i saksnummeret og merkelappet med navnet på åpningsraden.
#
# rolle=kohortnavn  : navnet gjelder i kohortvinduet 2023-09-01..2024-12-31 (23 kretser)
# rolle=forgjenger  : navn som gikk ut med domstolreformen (siste bruk før ${REFORM})
# rolle=etterfolger : navn som oppsto med oppsplittingen (første bruk fra ${SPLITT})
# rolle=sideform    : stavevarianter og engangsformer
# arvet_fra         : hvilke kohortkretser saker under dette navnet faktisk kom fra
#                     (utledet av sakene selv), med antall saker
#
# VARSEL: etter juni 2025 er navn -> krets IKKE en funksjon. RINGERIKE OG
# HALLINGDAL TINGRETT arver saker fra BÅDE RINGERIKE, ASKER OG BÆRUM og BUSKERUD.
# Grupper derfor på SAKENS EGEN åpningskode, aldri på navnet på utfallsraden.
#
# Kodene THODK, TFNOK, TVESK, TROGK, TOSLK, TBSKK, TSOLK, AUTEK, NOGUK, STROK,
# OBYFK er IKKE domstolskoder: de er en parserdefekt der saksnummerfeltet har
# svelget den påfølgende etiketten ("...KON-THODKjennelse avsagt:"). 3 406 rader
# bærer den svelgede etiketten; 52 av dem ville gitt korrupt domstolskode. Alle er
# normalisert bort ved å klippe ved "KJENNELSE".
#
# norsk_navn er satt inn der kunngjøringene bare bruker det nordsamiske navnet.
`
  + cols.join("\t") + "\n"
  + rader.map((r) => cols.map((c) => String(r[c] ?? "")).join("\t")).join("\n") + "\n";

writeFileSync(`${ROOT}/data/domstol-navnekart.tsv`, txt, "utf8");
console.log(`skrev data/domstol-navnekart.tsv  ${rader.length} rader` +
  `  sha256=${createHash("sha256").update(txt, "utf8").digest("hex")}`);

console.log("\nRolle-fordeling:");
const tell = {};
for (const r of rader) tell[r.rolle] = (tell[r.rolle] || 0) + 1;
console.table(tell);
console.log("\nEtterfølgernavn og hvor sakene deres kom fra:");
console.table(rader.filter((r) => r.rolle === "etterfolger" && r.arvet_fra)
  .map((r) => ({ etterfolger: r.navn, kode: r.kode, forste: r.forste, arvet_fra: r.arvet_fra })));

await closePool();
