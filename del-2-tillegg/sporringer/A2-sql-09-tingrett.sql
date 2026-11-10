-- A2/09 Er andelen med feltet stabil på tvers av tingretter? (publiseringspraksis-test)
WITH o AS (
  SELECT orgnr, min(dato) AS opened FROM kunngjoring.insolvens
  WHERE type='Konkurs - åpning' AND dato BETWEEN '2023-09-01' AND '2024-12-31' GROUP BY 1),
b AS (
  SELECT o.orgnr, o.opened,
         (SELECT max(nullif(trim(i.tingrett),'')) FROM kunngjoring.insolvens i
            WHERE i.orgnr=o.orgnr AND i.dato=o.opened AND i.type='Konkurs - åpning') AS tingrett,
         EXISTS (SELECT 1 FROM kunngjoring.felt x
                 WHERE x.orgnr=o.orgnr AND x.dato=o.opened
                   AND x.kunngj_type='Konkurs - åpning' AND x.felt='Åpnet etter') AS oppbud
  FROM o)
SELECT coalesce(tingrett,'(mangler)') AS tingrett, count(*) AS n,
       count(*) FILTER (WHERE oppbud) AS n_oppbud,
       round(100.0*count(*) FILTER (WHERE oppbud)/count(*),1) AS pct
FROM b GROUP BY 1 HAVING count(*) >= 25 ORDER BY 2 DESC;
