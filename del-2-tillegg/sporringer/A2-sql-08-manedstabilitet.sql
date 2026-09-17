-- A2/08 Er andelen med feltet stabil måned for måned i kohortvinduet?
WITH o AS (
  SELECT orgnr, min(dato) AS opened FROM kunngjoring.insolvens
  WHERE type='Konkurs - åpning' AND dato BETWEEN '2023-09-01' AND '2024-12-31' GROUP BY 1),
b AS (
  SELECT o.orgnr, o.opened,
         EXISTS (SELECT 1 FROM kunngjoring.felt x
                 WHERE x.orgnr=o.orgnr AND x.dato=o.opened
                   AND x.kunngj_type='Konkurs - åpning' AND x.felt='Åpnet etter') AS oppbud
  FROM o)
SELECT to_char(opened,'YYYY-MM') AS mnd, count(*) AS n,
       count(*) FILTER (WHERE oppbud) AS n_oppbud,
       round(100.0*count(*) FILTER (WHERE oppbud)/count(*),1) AS pct
FROM b GROUP BY 1 ORDER BY 1;
