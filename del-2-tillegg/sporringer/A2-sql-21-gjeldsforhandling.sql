-- A2/21 Restkanal: konkurs åpnet etter mislykket gjeldsforhandling (kkl. § 57).
-- Da er fristdagen dagen gjeldsforhandlingen ble åpnet (kkl. § 1-2 annet ledd),
-- og det finnes ingen oppbudsmerking. Hvor stor er kanalen i kohorten?
WITH o AS (
  SELECT orgnr, min(dato) AS opened FROM kunngjoring.insolvens
  WHERE type='Konkurs - åpning' AND dato BETWEEN '2023-09-01' AND '2024-12-31' GROUP BY 1),
b AS (
  SELECT o.orgnr, o.opened,
         EXISTS (SELECT 1 FROM kunngjoring.felt x
                 WHERE x.orgnr=o.orgnr AND x.dato=o.opened
                   AND x.kunngj_type='Konkurs - åpning' AND x.felt='Åpnet etter') AS oppbud,
         EXISTS (SELECT 1 FROM kunngjoring.kunngjoring k
                 WHERE k.orgnr=o.orgnr AND k.dato <= o.opened
                   AND (k.type ILIKE '%gjeldsforhandling%' OR k.type ILIKE '%rekonstruksjon%')) AS gjeldsforh
  FROM o)
SELECT CASE WHEN oppbud THEN 'oppbud' ELSE 'ingen_felt' END AS gruppe, count(*) AS n,
       count(*) FILTER (WHERE gjeldsforh) AS n_gjeldsforh,
       round(100.0*count(*) FILTER (WHERE gjeldsforh)/count(*),2) AS pct
FROM b GROUP BY 1 ORDER BY 1;
