// LANE 3 — domstol. Steg 12: er domstolsspennet ekte, eller binomisk støy?
// Kji-kvadrat homogenitetstest over de 16 publiserbare kretsene, pluss
// ankerregisteret som JSON til metodegrunnlaget.
// READ-ONLY. Kjøres: node domstol-12-homogenitet-og-ankere.mjs
import { readFileSync, writeFileSync } from "node:fs";
import { createHash } from "node:crypto";

const ROOT = "./del-1-hovedstudien";
const KJORT = new Date().toISOString().slice(0, 10);

// ---------- homogenitet ----------
const linjer = readFileSync(`${ROOT}/data/domstol-sluttabell.tsv`, "utf8")
  .split(/\r?\n/).filter((l) => l && !l.startsWith("#"));
const hode = linjer[0].split("\t");
const rader = linjer.slice(1).map((l) => Object.fromEntries(l.split("\t").map((v, i) => [hode[i], v])));
const pub = rader.filter((r) => r.publiserbar_n100 === "true")
  .map((r) => ({ krets: r.rettskrets, n: +r.saker, k: +r.innstilt,
                 median: +r.dager_median, km: +r.km_median_dager }));

const N = pub.reduce((s, r) => s + r.n, 0), K = pub.reduce((s, r) => s + r.k, 0);
const p0 = K / N;
let khi = 0;
for (const r of pub) {
  const e1 = r.n * p0, e0 = r.n * (1 - p0);
  khi += (r.k - e1) ** 2 / e1 + ((r.n - r.k) - e0) ** 2 / e0;
}
const df = pub.length - 1;
// p-verdi for kji-kvadrat via Wilson-Hilferty-approksimasjon
const wh = ((khi / df) ** (1 / 3) - (1 - 2 / (9 * df))) / Math.sqrt(2 / (9 * df));
const pKhi = 0.5 * (1 - erf(wh / Math.SQRT2)) * 2 / 2;
function erf(x) {
  const t = 1 / (1 + 0.3275911 * Math.abs(x));
  const y = 1 - (((((1.061405429 * t - 1.453152027) * t) + 1.421413741) * t - 0.284496736) * t + 0.254829592) * t * Math.exp(-x * x);
  return x >= 0 ? y : -y;
}
console.log(`HOMOGENITET over ${pub.length} rettskretser (n>=100), samlet andel ${(100*p0).toFixed(1)} %:`);
console.log(`  kji-kvadrat = ${khi.toFixed(2)}, df = ${df}, p ${pKhi < 1e-4 ? "< 0.0001" : "= " + pKhi.toFixed(4)}`);
console.log(`  (kritisk verdi 5 % ved df=${df} er 25.0; df=${df} forventer kji-kvadrat ~${df})`);

// hvor mye av spredningen er ekte? overdispersjonsandel
const overdisp = (khi - df) / khi;
console.log(`  andel av kji-kvadrat utover forventet støy: ${(100 * Math.max(0, overdisp)).toFixed(1)} %`);

// samme for varighet: Kruskal-Wallis er tyngre; vi rapporterer spennet i
// median og KM-median og lar overlappende KI tale.
const sortM = pub.slice().sort((a, b) => a.median - b.median);
const sortK = pub.slice().sort((a, b) => a.km - b.km);
console.log(`  median dager: ${sortM[0].median} (${sortM[0].krets}) – ${sortM[sortM.length-1].median} (${sortM[sortM.length-1].krets})`);
console.log(`  KM-median   : ${sortK[0].km} (${sortK[0].krets}) – ${sortK[sortK.length-1].km} (${sortK[sortK.length-1].krets})`);

// hvilke par har ikke-overlappende Clopper-Pearson-intervall?
const cp = rader.filter((r) => r.publiserbar_n100 === "true")
  .map((r) => ({ krets: r.rettskrets, lo: +r.cp95_lav, hi: +r.cp95_hoy, p: +r.andel_innstilt }));
let ikkeOverlapp = 0;
const par = [];
for (let i = 0; i < cp.length; i++) for (let j = i + 1; j < cp.length; j++) {
  if (cp[i].hi < cp[j].lo || cp[j].hi < cp[i].lo) { ikkeOverlapp++; par.push(`${cp[i].krets} vs ${cp[j].krets}`); }
}
console.log(`  par med ikke-overlappende 95 % Clopper-Pearson: ${ikkeOverlapp} av ${cp.length*(cp.length-1)/2}`);
par.slice(0, 12).forEach((p) => console.log(`    - ${p}`));

// ---------- ankerregister ----------
const ankere = {
  generert: KJORT,
  lane: "3 — domstol, varighet og ankere",
  merknad: "Datagrunnlaget omtales som offentlig tilgjengelige registerkunngjøringer. "
         + "Ingen kommersiell kilde inngår i eller er nevnt i denne studien.",
  ankere: [
    { navn: "SSB — Opna konkursar (statistikkside)",
      url: "https://www.ssb.no/virksomheter-foretak-og-regnskap/konkurser/statistikk/opna-konkursar",
      status: "VERIFISERT", hentet: KJORT,
      sitat: "950 opna konkursar 2026K2; 237 innanfor bygge- og anleggsverksemd.",
      bruk: "Skala og ferskhet på åpningstallene. Siden rapporterer INGEN utfall, varighet eller domstol." },
    { navn: "SSB — Konkursar, Om statistikken",
      url: "https://www.ssb.no/virksomheter-foretak-og-regnskap/statistikker/konkurs",
      status: "VERIFISERT", hentet: KJORT,
      sitat: "Kjelde: Konkursregisteret i Brønnøysundregistera; data overførast elektronisk den 17. kvar månad. Statistikken dekkjer opna konkursar.",
      bruk: "Beviset for hullet vi fyller: offentlig statistikk teller åpninger, ikke boets utfall." },
    { navn: "SSB statistikkbanken tabell 09122 (API)",
      url: "https://data.ssb.no/api/v0/no/table/09122",
      status: "VERIFISERT", hentet: KJORT,
      sitat: "09122: Opna konkursar, etter næring, konkurstype, statistikkvariabel og kvartal. Tid: 2010K1–2026K2.",
      bruk: "Kalibrering av åpningsvolum per kvartal og næring; eneste legitime historiske serie (L1)." },
    { navn: "SSB statistikkbanken tabell 07165 (API)",
      url: "https://data.ssb.no/api/v0/no/table/07165",
      status: "VERIFISERT", hentet: KJORT,
      sitat: "07165: Konkurser, etter region, næring (SN2007), organisasjonsform, statistikkvariabel og kvartal. Tid: 2006K1–2026K2.",
      bruk: "Regional kalibrering. Merk: næringsaksen er SN2007, jf. vintage-sømmen (L17)." },
    { navn: "Brønnøysundregistrene — kunngjøringer fra Konkursregisteret",
      url: "https://www.brreg.no/en/searching-our-registers/announcements/about-announcements/announcements-from-the-register-of-bankruptcies/",
      status: "VERIFISERT", hentet: KJORT,
      sitat: "The announcements will normally be available on the same day as the bankruptcy order has been made.",
      bruk: "Lisensen for å bruke kunngjøringsdatoen som hendelsesdato. Åtte kunngjøringstyper, inkludert innstilling og avslutning av bobehandling." },
    { navn: "Ot.prp. nr. 26 (1998-99) Del 4 punkt 1.1",
      url: "https://www.regjeringen.no/no/dokumenter/otprp-nr-26-1998-99-/id159514/?ch=4",
      status: "VERIFISERT", hentet: KJORT,
      sitat: "Samtidig har det skjedd en utvikling i retning av at en stadig større andel av konkursboene blir innstilt uten at det skjer noen utbetaling til kreditorene, fordi boets midler ikke engang strekker til å bekoste selve bobehandlingen (konkursloven § 135). I 1996 ble således så mange som tre av fire boer innstilt av denne grunn, mens tallene i 1976 var to av fem boer.",
      bruk: "Historisk anker (1976/1996) OG den juridiske definisjonen av innstilling etter kkl. § 135, i samme setning. Erstatter konkursradet.no, som svarer 403 på verktøy.",
      presisering: "Kapittelhenvisningen er Del 4 punkt 1.1 (URL ?ch=4), ikke dokumentets kap. 1.1 (som er Del 1)." },
    { navn: "Forbrukerrådet — Konkurs",
      url: "https://www.forbrukerradet.no/forside/okonomi-og-betaling/konkurs/",
      status: "VERIFISERT", hentet: KJORT,
      sitat: "Ver likevel klar over at for forbrukaren er det ofte ikkje noko å hente i konkursbuet.",
      bruk: "Forbrukerrammen vi tallfester. Står i avsnittet «Kva gjer du når seljar går konkurs?»." },
    { navn: "Norges domstoler — Elleve nye tingretter fra 10. juni (2025)",
      url: "https://www.domstol.no/no/aktuelt/2025/elleve-nye-tingretter-fra-10.-juni",
      status: "VERIFISERT", hentet: KJORT,
      sitat: "Fra 10. juni får vi elleve nye tingretter.",
      bruk: "Forklarer navnedriften i utfallskunngjøringene fra juni 2025: Vestre Innlandet, Telemark, Møre og Romsdal, Buskerud, Ringerike/Asker og Bærum og Hordaland ble delt. Kohortvinduet ligger FØR delingen." },
    { navn: "Store norske leksikon / Norges domstoler — domstolreformen 2021",
      url: "https://snl.no/domstolsreformen",
      status: "VERIFISERT", hentet: KJORT,
      sitat: "Fra 26. april 2021 ble antall rettskretser redusert fra 59 til 23.",
      bruk: "Kohortvinduet (åpninger 2023-09-01..2024-12-31) ligger helt inne i 23-krets-perioden. Materialet viser nøyaktig 23 kretser — ekstern og intern telling stemmer." },
    { navn: "Norges domstoler — Sis- ja Nuorta-Finnmárkku diggegoddi / Indre og Østre Finnmark tingrett",
      url: "https://www.domstol.no/no/domstoler/tingrett/sis--ja-nuorta-finnmarkku-diggegoddi--indre-og-ostre-finnmark-tingrett/",
      status: "VERIFISERT", hentet: KJORT,
      sitat: "Sis- ja Nuorta-Finnmárkku diggegoddi / Indre og Østre Finnmark tingrett",
      bruk: "Kunngjøringene bruker bare det nordsamiske navnet. Norsk navn må settes inn i publiserte tabeller." },
    { navn: "Konkursrådet — konkursradet.no",
      url: "https://www.konkursradet.no/",
      status: "UBEKREFTET", hentet: KJORT,
      sitat: "",
      bruk: "Svarer HTTP 403 på verktøy. IKKE sitert. § 135 er i stedet forankret i Ot.prp. nr. 26 (1998-99) Del 4 punkt 1.1." },
  ],
};
const j = JSON.stringify(ankere, null, 2) + "\n";
writeFileSync(`${ROOT}/data/domstol-ankere.json`, j, "utf8");
console.log(`\nskrev data/domstol-ankere.json  sha256=${createHash("sha256").update(j, "utf8").digest("hex")}`);
