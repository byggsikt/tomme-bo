// bransje-11: kan en avvikende bransje-verdi ha gått tapt i dedupliseringen?
// kunngjoring.insolvens har 13 646 rader for 13 644 selskaper, mens råtabellen har
// 26 807 rader. Er dedupliseringen en nøkkelbegrensning (som ville avvist en
// avvikende annenkopi) eller et DISTINCT (som ville beholdt den)?
// READ-ONLY — leser bare katalogen.
import { q, done, writeJson, RUN_DATE } from "./_lib.mjs";

const out = { kjoredato: RUN_DATE };

out.begrensninger = (await q(`
  select con.conname, con.contype,
         pg_get_constraintdef(con.oid) as definisjon
  from pg_constraint con
  join pg_class rel on rel.oid = con.conrelid
  join pg_namespace ns on ns.oid = rel.relnamespace
  where ns.nspname = 'kunngjoring' and rel.relname = 'insolvens'
`)).rows;

out.indekser = (await q(`
  select indexname, indexdef from pg_indexes
  where schemaname = 'kunngjoring' and tablename = 'insolvens'
`)).rows;

out.er_visning = (await q(`
  select c.relkind
  from pg_class c join pg_namespace n on n.oid = c.relnamespace
  where n.nspname = 'kunngjoring' and c.relname = 'insolvens'
`)).rows;

// samme nøkkel på tvers av HELE insolvens-tabellen, ikke bare åpninger
out.nokkelunikhet = (await q(`
  select count(*) as rader,
         count(distinct (orgnr, dato, type)) as unike_orgnr_dato_type
  from kunngjoring.insolvens
`)).rows[0];

writeJson(`data/bransje-insolvens-integritet_${RUN_DATE}.json`, out);
console.log(JSON.stringify(out, null, 2));
await done();
