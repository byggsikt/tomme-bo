// B3: classify the cohort's bransje labels with the STUDY's canonical cascade (read-only module, no DB).
import { readFileSync, writeFileSync } from "node:fs";
import { slaaOpp, erByggF, erByggUtforende } from "file:///./kohort-bransjeklassifikator.mjs";
const lines = readFileSync("B3-01-kohort-pull.txt", "utf8").split(/\r?\n/).filter(Boolean);
const labels = new Set();
for (const l of lines) { const f = l.split("|"); labels.add(f[5]); }
const out = ["etikett\tkode\tkilde\tvintage\tbygg_F\tbygg_U"];
for (const raw of labels) {
  const lab = raw.replace(/<NL>/g, "\n");
  const t = slaaOpp(lab);
  out.push([raw, t.kode ?? "", t.kilde ?? "", t.vintage ?? "", erByggF(t.kode) ? 1 : 0, erByggUtforende(t.kode) ? 1 : 0].join("\t"));
}
writeFileSync("B3-02-klassifisering.tsv", out.join("\n") + "\n", "utf8");
console.log("labels:", labels.size);
