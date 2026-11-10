// LANE 1 — bransje-etikett -> NACE. Delt modul (READ-ONLY, ingen DB-tilgang her).
//
// Etiketten i kunngjoringen er naeringens NAVN slik Bronnoysund skriver det, avkortet
// ved 60 tegn og deretter trimmet. Den maa oversettes til kode uten a se paa selskapet
// (doed-NACE-fellen: 97 % av slettede selskaper har ingen naeringskode).
// Fasit er den offisielle standarden: SSB Klass klassifikasjon 6, versjon 30 (SN2007)
// og 3218 (SN2025). Begge vintager lastes fordi kunngjoringskorpuset har en som
// 2025-09-01 (L17): for sommen SN2007-navn, etter sommen SN2025-navn.
//
// Oppslagskaskaden, strengest forst. Hvert steg krever at alle kandidatkoder deler
// samme tosifrede naering — ellers markeres etiketten som tvetydig og telles ikke.
import { readFileSync } from "node:fs";

const DATA = "./data";
const norm = (s) => (s || "").replace(/\u00a0/g, " ").replace(/\s+/g, " ").trim();
const to = (k) => (k || "").slice(0, 2);

function lastVintage(fil, merke) {
  const koder = JSON.parse(readFileSync(`${DATA}/${fil}`, "utf8")).koder;
  const eksakt = new Map(), avkortet = new Map(), navn = [];
  for (const k of koder) {
    const n = norm(k.name);
    if (!n) continue;
    navn.push({ navn: n, kode: k.code });
    (eksakt.get(n) || eksakt.set(n, []).get(n)).push(k.code);
    const t = n.slice(0, 60).trimEnd();
    (avkortet.get(t) || avkortet.set(t, []).get(t)).push(k.code);
  }
  navn.sort((a, b) => b.navn.length - a.navn.length); // lengst forst
  return { merke, eksakt, avkortet, navn };
}

const V = [lastVintage("ssb-klass-sn2007.json", "SN2007"),
           lastVintage("ssb-klass-sn2025.json", "SN2025")];

// Etiketter kunngjoringen bruker som IKKE er naeringer — de skal aldri klassifiseres.
export const IKKE_NAERING = new Set(["Uoppgitt", "Enheten er slettet", "Ikke oppgitt"]);

function enig(koder) {
  const t = new Set(koder.map(to));
  return t.size === 1 ? koder.slice().sort()[0] : null;
}

/** Slaar opp en bransje-etikett. Returnerer {kode, kilde, vintage} eller {kode:null, kilde:...}. */
export function slaaOpp(etikettRaa) {
  if (!etikettRaa) return { kode: null, kilde: "tom" };
  // Flere naeringer skilles med linjeskift; hovednaeringen staar forst.
  const etikett = norm(etikettRaa.split("\n")[0]);
  if (!etikett) return { kode: null, kilde: "tom" };
  if (IKKE_NAERING.has(etikett)) return { kode: null, kilde: "ikke_naering" };

  for (const v of V) {
    const e = v.eksakt.get(etikett);
    if (e) { const k = enig(e); if (k) return { kode: k, kilde: "eksakt", vintage: v.merke }; }
  }
  for (const v of V) {
    const a = v.avkortet.get(etikett);
    if (a) { const k = enig(a); if (k) return { kode: k, kilde: "avkortet60", vintage: v.merke }; }
  }
  // Etiketten er et prefiks av det offisielle navnet (kilden kappet midt i et ord).
  for (const v of V) {
    const treff = v.navn.filter(x => x.navn.startsWith(etikett)).map(x => x.kode);
    if (treff.length) { const k = enig(treff); if (k) return { kode: k, kilde: "etikett_er_prefiks", vintage: v.merke }; }
  }
  // Det offisielle navnet er et prefiks av etiketten (kilden har lagt paa en presisering,
  // f.eks. «Blikkenslagerarbeid paa tak» mot SN2007 43.911 «Blikkenslagerarbeid»).
  for (const v of V) {
    const kand = v.navn.filter(x => x.navn.length >= 8 &&
      (etikett === x.navn || etikett.startsWith(x.navn + " ")));
    if (kand.length) {
      const lengst = kand[0].navn.length;
      const k = enig(kand.filter(x => x.navn.length === lengst).map(x => x.kode));
      if (k) return { kode: k, kilde: "offisielt_navn_er_prefiks", vintage: v.merke };
    }
  }
  // Hengende bindestrek: kunngjoringen skriver «Interiorarkitekt, interiordesign og ...»
  // der standarden skriver «Interiorarkitekt-, interiordesign- og ...». Samme navn.
  const utenHengende = (s) => s.replace(/-(?=[,\s])/g, "");
  const e2 = utenHengende(etikett);
  if (e2 !== etikett) {
    for (const v of V) {
      const treff = v.navn.filter(x => utenHengende(x.navn).startsWith(e2)).map(x => x.kode);
      if (treff.length) { const k = enig(treff); if (k) return { kode: k, kilde: "hengende_bindestrek", vintage: v.merke }; }
    }
  }
  return { kode: null, kilde: "ingen_treff" };
}

// To bygg-definisjoner. Forskjellen er 41.1 «Utvikling av byggeprosjekter»
// (eiendomsutvikling), som ligger inne i SSBs naeringsomraade F men ikke er
// utforende bygge- og anleggsvirksomhet. Begge rapporteres; de gir ulike tall.
export const erByggF = (k) => !!k && /^(41|42|43)/.test(k);
export const erByggUtforende = (k) => !!k && (/^(42|43)/.test(k) || (/^41/.test(k) && !/^41\.1/.test(k)));
