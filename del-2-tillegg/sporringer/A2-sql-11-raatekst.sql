-- A2/11 Brødteksten: kunngjoring.type er tittel+brødtekst avkortet ved 80 tegn (L13).
-- Sier den noe om grunnlaget? Eksempler fra begge grupper.
WITH o AS (
  SELECT orgnr, min(dato) AS opened FROM kunngjoring.insolvens
  WHERE type='Konkurs - åpning' AND dato BETWEEN '2023-09-01' AND '2024-12-31' GROUP BY 1),
b AS (
  SELECT o.orgnr, o.opened,
         EXISTS (SELECT 1 FROM kunngjoring.felt x
                 WHERE x.orgnr=o.orgnr AND x.dato=o.opened
                   AND x.kunngj_type='Konkurs - åpning' AND x.felt='Åpnet etter') AS oppbud
  FROM o)
SELECT CASE WHEN b.oppbud THEN 'oppbud' ELSE 'ingen_felt' END AS gruppe,
       k.type, count(*) AS n
FROM b JOIN kunngjoring.kunngjoring k
  ON k.orgnr=b.orgnr AND k.dato=b.opened AND k.type LIKE 'Konkurs%'
GROUP BY 1,2 ORDER BY 3 DESC LIMIT 15;
