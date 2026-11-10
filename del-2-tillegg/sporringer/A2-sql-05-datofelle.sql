-- A2/05 DATO-FELLE: en konkurs kunngjøres i TO registre (L8). Hvis registrene
-- kunngjør på ULIKE datoer, og bare det ene trykker «Åpnet etter», vil
-- min(dato)-låsen i kohort-SQL-en skjule feltet. Test: finnes feltet på en ANNEN
-- dato for de 1 431 uten?
WITH o AS (
  SELECT orgnr, min(dato) AS opened FROM kunngjoring.insolvens
  WHERE type='Konkurs - åpning' AND dato BETWEEN '2023-09-01' AND '2024-12-31' GROUP BY 1),
b AS (
  SELECT o.orgnr, o.opened,
         EXISTS (SELECT 1 FROM kunngjoring.felt x
                 WHERE x.orgnr=o.orgnr AND x.dato=o.opened
                   AND x.kunngj_type='Konkurs - åpning' AND x.felt='Åpnet etter') AS oppbud_paa_dato,
         EXISTS (SELECT 1 FROM kunngjoring.felt x
                 WHERE x.orgnr=o.orgnr AND x.felt='Åpnet etter') AS oppbud_noen_dato,
         (SELECT count(DISTINCT i2.dato) FROM kunngjoring.insolvens i2
            WHERE i2.orgnr=o.orgnr AND i2.type='Konkurs - åpning') AS n_aapningsdatoer
  FROM o)
SELECT oppbud_paa_dato, oppbud_noen_dato, count(*) AS n,
       round(avg(n_aapningsdatoer),3) AS snitt_aapningsdatoer,
       max(n_aapningsdatoer) AS maks_aapningsdatoer
FROM b GROUP BY 1,2 ORDER BY 1,2;
