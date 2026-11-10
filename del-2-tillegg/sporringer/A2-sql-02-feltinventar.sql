-- A2/02 Feltinventar på Konkurs - åpning i kohorten: hvilke felt finnes, og
-- hvor ofte, delt på om «Åpnet etter» er der eller ikke.
WITH o AS (
  SELECT orgnr, min(dato) AS opened FROM kunngjoring.insolvens
  WHERE type='Konkurs - åpning' AND dato BETWEEN '2023-09-01' AND '2024-12-31' GROUP BY 1),
b AS (
  SELECT o.orgnr, o.opened,
         EXISTS (SELECT 1 FROM kunngjoring.felt x
                 WHERE x.orgnr=o.orgnr AND x.dato=o.opened
                   AND x.kunngj_type='Konkurs - åpning' AND x.felt='Åpnet etter') AS oppbud
  FROM o)
SELECT f.felt,
       count(*) FILTER (WHERE b.oppbud)                      AS n_oppbud,
       count(*) FILTER (WHERE NOT b.oppbud)                  AS n_ingen_felt
FROM b JOIN kunngjoring.felt f
  ON f.orgnr=b.orgnr AND f.dato=b.opened AND f.kunngj_type='Konkurs - åpning'
GROUP BY 1
ORDER BY (count(*)) DESC
LIMIT 60;
