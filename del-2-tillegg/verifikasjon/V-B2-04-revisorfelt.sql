-- last value of felt 'Revisor' before opening, and whether an auditor was named at that point
WITH o AS (SELECT orgnr, min(dato) AS opened FROM kunngjoring.insolvens WHERE type='Konkurs - åpning' AND dato BETWEEN '2023-09-01' AND '2024-12-31' GROUP BY 1),
l AS (SELECT DISTINCT ON (f.orgnr) f.orgnr, f.dato, f.verdi
      FROM kunngjoring.felt f JOIN o USING (orgnr) WHERE f.felt='Revisor' AND f.dato < o.opened
      ORDER BY f.orgnr, f.dato DESC)
SELECT CASE WHEN verdi IS NULL THEN 'ingen Revisor-felt' WHEN verdi ILIKE 'Utgår%' THEN 'Utgår (revisor fjernet)' ELSE 'Revisor navngitt' END AS st, count(*)
FROM o LEFT JOIN l USING (orgnr) GROUP BY 1 ORDER BY 2 DESC;
SELECT '--- per-orgnr csv ---';
WITH o AS (SELECT orgnr, min(dato) AS opened FROM kunngjoring.insolvens WHERE type='Konkurs - åpning' AND dato BETWEEN '2023-09-01' AND '2024-12-31' GROUP BY 1),
l AS (SELECT DISTINCT ON (f.orgnr) f.orgnr, f.dato, f.verdi
      FROM kunngjoring.felt f JOIN o USING (orgnr) WHERE f.felt='Revisor' AND f.dato < o.opened
      ORDER BY f.orgnr, f.dato DESC)
SELECT o.orgnr, CASE WHEN l.verdi IS NULL THEN 'ingen' WHEN l.verdi ILIKE 'Utgår%' THEN 'utgaar' ELSE 'navngitt' END AS rev_state
FROM o LEFT JOIN l USING (orgnr) ORDER BY 1;
