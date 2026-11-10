import { slaaOpp, erByggF, erByggUtforende } from "file:///./kohort-bransjeklassifikator.mjs";
for (const e of ["Oppføring av bygninger","Snekkerarbeid","Utvikling og salg av egen fast eiendom ellers","Uoppgitt","Blikkenslagerarbeid på tak","Drift av restauranter og kafeer"]) {
  const t = slaaOpp(e); console.log(JSON.stringify({e, ...t, F: erByggF(t.kode), U: erByggUtforende(t.kode)}));
}
