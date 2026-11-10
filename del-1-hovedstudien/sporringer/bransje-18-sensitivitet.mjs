// bransje-18: sensitivitet. Er byggnæringens lavere innstillingsandel robust for
// at bygg har flere bo som ennå ikke er avgjort (8,86 % mot 6,16 %)?
// Vi lar de fortsatt åpne boene i BEGGE gruppene bli innstilt med samme rate x
// og ser om rekkefølgen kan snu. Ingen databasetilgang; ren regning på tallene
// fra bransje-17 (uavhengig rekontroll).
import { writeJson, clopperPearson, RUN_DATE } from "./_lib.mjs";

const bygg = { innstilt: 1016, apen: 125, n: 1411 };
const ovrige = { innstilt: 2767, apen: 224, n: 3634 };

const kurve = [];
for (let i = 0; i <= 20; i++) {
  const x = i / 20;
  const pb = (bygg.innstilt + x * bygg.apen) / bygg.n;
  const pr = (ovrige.innstilt + x * ovrige.apen) / ovrige.n;
  kurve.push({ x, bygg_pst: 100 * pb, ovrige_pst: 100 * pr, differanse_pp: 100 * (pb - pr) });
}
const kryss = (ovrige.innstilt * bygg.n - bygg.innstilt * ovrige.n) /
              (bygg.apen * ovrige.n - ovrige.apen * bygg.n);

const [blo, bhi] = clopperPearson(bygg.innstilt, bygg.n);
const [rlo, rhi] = clopperPearson(ovrige.innstilt, ovrige.n);

const out = {
  kjoredato: RUN_DATE,
  utgangspunkt: {
    bygg: { ...bygg, pst: (100 * bygg.innstilt) / bygg.n, ki95: [100 * blo, 100 * bhi] },
    ovrige: { ...ovrige, pst: (100 * ovrige.innstilt) / ovrige.n, ki95: [100 * rlo, 100 * rhi] },
    differanse_pp: (100 * bygg.innstilt) / bygg.n - (100 * ovrige.innstilt) / ovrige.n,
    khikvadrat_yates: 9.051, p_verdi: 0.00262,
    newcombe_ki95_differanse_pp: [-6.89, -1.45],
    fortsatt_apent_khikvadrat_yates: 11.049, fortsatt_apent_p: 0.000887,
  },
  sensitivitet: {
    beskrivelse: "x = andelen av de fortsatt åpne boene som til slutt blir innstilt, antatt lik i begge grupper",
    kurve,
    krysningspunkt_x: kryss,
    konklusjon: kryss > 1 || kryss < 0
      ? "Rekkefølgen kan ikke snu for noen felles oppløsningsrate mellom 0 og 1: byggnæringen ligger lavere uansett. Gapet krymper fra -4,14 til -1,44 prosentpoeng."
      : "Rekkefølgen KAN snu innenfor [0,1] — konklusjonen er ikke robust.",
  },
};
const f = writeJson(`data/bransje-sensitivitet_${RUN_DATE}.json`, out);
console.log(JSON.stringify({ ...out, sensitivitet: { ...out.sensitivitet, kurve: `${kurve.length} punkter` }, fil: f }, null, 2));
