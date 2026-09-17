-- A2/06 Registermiks: kunngjøres åpningene av de samme registrene i begge grupper?
WITH o AS (
  SELECT orgnr, min(dato) AS opened FROM kunngjoring.insolvens
  WHERE type='Konkurs - åpning' AND dato BETWEEN '2023-09-01' AND '2024-12-31' GROUP BY 1),
b AS (
  SELECT o.orgnr, o.opened,
         EXISTS (SELECT 1 FROM kunngjoring.felt x
                 WHERE x.orgnr=o.orgnr AND x.dato=o.opened
                   AND x.kunngj_type='Konkurs - åpning' AND x.felt='Åpnet etter') AS oppbud
  FROM o),
r AS (
  SELECT b.orgnr, b.oppbud,
         string_agg(DISTINCT coalesce(nullif(trim(k.register),''),'(tom)'), '+' ORDER BY coalesce(nullif(trim(k.register),''),'(tom)')) AS registre,
         count(DISTINCT k.kid) AS n_kid
  FROM b LEFT JOIN kunngjoring.kunngjoring k
    ON k.orgnr=b.orgnr AND k.dato=b.opened AND k.type LIKE 'Konkurs - åpning%'
  GROUP BY 1,2)
SELECT CASE WHEN oppbud THEN 'oppbud' ELSE 'ingen_felt' END AS gruppe,
       coalesce(registre,'(ingen rad)') AS registre, count(*) AS n
FROM r GROUP BY 1,2 ORDER BY 1,3 DESC;
