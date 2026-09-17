// V-B3: independent classification of the cohort's bransje labels with the STUDY's canonical cascade.
// Reads V-B3-01-kohort.txt (pipe-separated), writes V-B3-02-kohort-klassifisert.tsv (orgnr + tag columns).
import { readFileSync, writeFileSync } from "node:fs";
import { slaaOpp, erByggF, erByggUtforende } from "file:///./kohort-bransjeklassifikator.mjs";

const DIR = "../data";
const lines = readFileSync(`${DIR}/V-B3-01-kohort.txt`, "utf8").split(/\r?\n/).filter(Boolean);

const cache = new Map();
function tag(raw) {
  if (cache.has(raw)) return cache.get(raw);
  const lab = (raw || "").replace(/<NL>/g, "\n");
  const t = slaaOpp(lab);
  const r = { kode: t.kode ?? "", kilde: t.kilde ?? "", vintage: t.vintage ?? "",
              F: erByggF(t.kode) ? 1 : 0, U: erByggUtforende(t.kode) ? 1 : 0 };
  cache.set(raw, r);
  return r;
}

const out = ["orgnr\tbransje\tnace\tkilde\tvintage\tbygg_F\tbygg_U"];
let nU = 0, nF = 0, nNull = 0;
for (const l of lines) {
  const f = l.split("|");
  const orgnr = f[0], bransje = f[5];
  const t = tag(bransje);
  if (t.U) nU++;
  if (t.F) nF++;
  if (!t.kode) nNull++;
  out.push([orgnr, bransje, t.kode, t.kilde, t.vintage, t.F, t.U].join("\t"));
}
writeFileSync(`${DIR}/V-B3-02-kohort-klassifisert.tsv`, out.join("\n") + "\n", "utf8");
console.log(JSON.stringify({ rader: lines.length, unike_etiketter: cache.size, bygg_utforende: nU, bygg_F: nF, uklassifiserbar: nNull }));
