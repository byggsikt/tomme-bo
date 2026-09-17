// LANE 1 / kohort — FIGURGRUNNLAG (READ-ONLY).
// Skriver tallgrunnlaget for hovedfiguren («1 000 konkursbo»-fossefallet) og for
// bransje-/domstolsfigurene. Alle celler n >= 10. Ingen orgnr, ingen navn.
import { getPool, closePool } from "./db.mjs";
import { writeFileSync } from "node:fs";
import { createHash } from "node:crypto";
import { slaaOpp, erByggUtforende, erByggF } from "./kohort-bransjeklassifikator.mjs";

const FIG = "./figurer";
const KJORT = new Date().toISOString().slice(0, 10);
const FRA = "2023-09-01", TIL = "2024-12-31";
const pool = getPool();
const sha = (s) => createHash("sha256").update(s).digest("hex");
const out = (l, r) => { console.log("\n=== " + l + " ==="); console.log(JSON.stringify(r, null, 1)); };
const skrevet = [];
function skrivCsv(sti, rader) {
  const kol = rader.length ? Object.keys(rader[0]) : [];
  const esc = (v) => v === null || v === undefined ? "" : (/[",\n;]/.test(String(v)) ? '"' + String(v).replace(/"/g, '""') + '"' : String(v));
  const csv = [kol.join(";"), ...rader.map(r => kol.map(k => esc(r[k])).join(";"))].join("\n") + "\n";
  writeFileSync(sti, csv, "utf8");
  skrevet.push({ fil: sti.split("/").pop(), rader: rader.length, sha256: sha(csv) });
}
try {
  await pool.query("set statement_timeout = '900s'");
  const rader = (await pool.query(`
    with aapning as materialized (
      select orgnr, min(dato) as d from kunngjoring.insolvens where type='Konkurs - åpning' group by orgnr
    ),
    k as materialized (select orgnr, d from aapning where d between $1::date and $2::date),
    innst as materialized (select distinct orgnr from kunngjoring.insolvens where type='Konkurs - innstilling av bobehandlingen'),
    avsl  as materialized (select distinct orgnr from kunngjoring.insolvens where type='Konkurs - avslutning av bobehandlingen')
    select nullif(trim(i.bransje),'') as bransje,
           (n.orgnr is not null) as innstilt, (a.orgnr is not null) as avsluttet
    from k
    join kunngjoring.insolvens i on i.orgnr=k.orgnr and i.dato=k.d and i.type='Konkurs - åpning'
    left join innst n on n.orgnr=k.orgnr
    left join avsl  a on a.orgnr=k.orgnr
  `, [FRA, TIL])).rows;
  for (const r of rader) { const t = slaaOpp(r.bransje); r.byggU = erByggUtforende(t.kode); r.byggF = erByggF(t.kode); }

  // ---- FOSSEFALL: per 1 000 bo, alle og bygg
  const foss = [["ALLE naeringer", rader], ["BYGG (utforende)", rader.filter(r => r.byggU)],
                ["OVRIGE naeringer", rader.filter(r => !r.byggU)]].map(([navn, d]) => {
    const n = d.length;
    const i = d.filter(r => r.innstilt && !r.avsluttet).length;
    const a = d.filter(r => r.avsluttet && !r.innstilt).length;
    const b = d.filter(r => r.innstilt && r.avsluttet).length;
    const o = n - i - a - b;
    const p = (x) => Math.round(1000 * x / n);
    return { gruppe: navn, bo: n,
             per1000_innstilt: p(i), per1000_avsluttet: p(a),
             per1000_begge_kunngjoringer: p(b), per1000_fortsatt_apne: p(o),
             antall_innstilt: i, antall_avsluttet: a, antall_begge: b, antall_apne: o };
  });
  out("FOSSEFALL — per 1 000 konkursbo", foss);
  skrivCsv(`${FIG}/fossefall-per-1000-bo-${KJORT}.csv`, foss);

  // ---- HISTORISK TREPUNKTSLINJE. 1976/1996 er IKKE vaare tall og maa ikke fremstilles
  // som en serie fra vaart materiale (L1). De staar som eksterne, siterte punkter.
  const alle = foss[0];
  const trepunkt = [
    { aar: 1976, andel_innstilt_pst: 40, kilde: "Ot.prp. nr. 26 (1998-99) — «to av fem»", status: "UBEKREFTET, maa bekreftes i dokumentet for trykk" },
    { aar: 1996, andel_innstilt_pst: 75, kilde: "Ot.prp. nr. 26 (1998-99) — «tre av fire»", status: "UBEKREFTET, maa bekreftes i dokumentet for trykk" },
    { aar: 2024, andel_innstilt_pst: +(100 * (alle.antall_innstilt + alle.antall_begge) / alle.bo).toFixed(1),
      kilde: "Byggsikt, kohort " + FRA + ".." + TIL + " (n=" + alle.bo + ")", status: "MAALT" },
  ];
  out("TREPUNKTSLINJE 1976 -> 1996 -> 2024 (de to forste er siterte, ikke maalte)", trepunkt);
  skrivCsv(`${FIG}/historisk-trepunktslinje-${KJORT}.csv`, trepunkt);
  out("FILER", skrevet);
} catch (e) { console.error("FEIL:", e.message, e.stack); } finally { await closePool(); }
