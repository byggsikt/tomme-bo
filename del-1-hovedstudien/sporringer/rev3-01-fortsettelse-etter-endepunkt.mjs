// rev3-01 — § 139-sensitivitet. Kom noen «fortsettelse av bobehandling» ETTER et primært
// endepunkt (§ 135-innstilling eller ordinær avslutning) i kohorten?
//
// READ-ONLY, ingen databasetilgang: kjøres på det frosne kohortuttrekket
// data/_kohort-rader-arbeidskopi.json (5 165 forløp), samme kilde som rev2-serien.
// Datagrunnlag: offentlig tilgjengelige registerkunngjøringer. Korpusslutt 2026-08-24.
import { readFileSync, writeFileSync } from "node:fs";
import { createHash } from "node:crypto";

const ROOT = "./del-1-hovedstudien";
const raw = readFileSync(`${ROOT}/data/_kohort-rader-arbeidskopi.json`, "utf8");
const rows = JSON.parse(raw);
const sha = createHash("sha256").update(raw).digest("hex");

const d = (v) => (v ? String(v).slice(0, 10) : null);

let medForts = 0, fortsEtterInnstilling = 0, fortsEtterAvslutning = 0,
    fortsForEndepunkt = 0, fortsUtenEndepunkt = 0, sammeDag = 0;
const detaljer = [];

for (const r of rows) {
  const f = d(r.fortsettelse); if (!f) continue;
  medForts++;
  const inn = d(r.innstilling), avs = d(r.avslutning);
  const etterInn = inn && f > inn, etterAvs = avs && f > avs;
  const likInn = inn && f === inn, likAvs = avs && f === avs;
  if (etterInn) fortsEtterInnstilling++;
  if (etterAvs) fortsEtterAvslutning++;
  if (likInn || likAvs) sammeDag++;
  if (!inn && !avs) fortsUtenEndepunkt++;
  else if (!etterInn && !etterAvs && !likInn && !likAvs) fortsForEndepunkt++;
  detaljer.push({
    utfall: r.utfall, bygg: !!r.bygg_utforende,
    rekkefolge: !inn && !avs ? "kun_fortsettelse"
      : etterInn ? "fortsettelse_ETTER_innstilling"
      : etterAvs ? "fortsettelse_ETTER_avslutning"
      : (likInn || likAvs) ? "samme_dag_som_endepunkt"
      : "fortsettelse_FOR_endepunkt",
    dager_forts_til_innstilling: inn ? Math.round((Date.parse(inn) - Date.parse(f)) / 86400000) : null,
    dager_forts_til_avslutning: avs ? Math.round((Date.parse(avs) - Date.parse(f)) / 86400000) : null,
  });
}

const resultat = {
  kjort: "2026-08-31", korpusslutt: "2026-08-24", kilde_sha256: sha,
  kohort: rows.length,
  forlop_med_fortsettelse: medForts,
  fortsettelse_etter_135_innstilling: fortsEtterInnstilling,
  fortsettelse_etter_ordinaer_avslutning: fortsEtterAvslutning,
  fortsettelse_samme_dag_som_endepunkt: sammeDag,
  fortsettelse_for_endepunkt: fortsForEndepunkt,
  fortsettelse_uten_registrert_endepunkt: fortsUtenEndepunkt,
  konklusjon: (fortsEtterInnstilling + fortsEtterAvslutning) === 0
    ? "Ingen fortsettelse er kunngjort etter et primaert endepunkt i kohorten. Foerste-utfall-regelen er dermed ikke i konflikt med noen observert gjenopptakelse."
    : "MINST ETT forloep har fortsettelse etter et primaert endepunkt - maa adjudiseres eksplisitt i teksten.",
  detaljer,
};

writeFileSync(`${ROOT}/data/rev3-01-fortsettelse-sensitivitet_2026-08-31.json`,
  JSON.stringify(resultat, null, 2), "utf8");
console.log(JSON.stringify({ ...resultat, detaljer: `${detaljer.length} forløp (i fila)` }, null, 1));
