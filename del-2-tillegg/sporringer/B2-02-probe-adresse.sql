-- B2 probe 2: how does adresse.kommune vary within one company (spelling variants vs real moves)?
SELECT 'adr_811557722' AS hva, a.dato, a.kilde, left(a.gate,30) AS gate, a.postnr, a.sted, a.kommune, kunngjoring.kanoniser_type(a.kunngj_type) AS kt
FROM kunngjoring.adresse a WHERE a.orgnr='811557722' AND a.dato >= DATE '2022-09-01' ORDER BY a.dato, a.kilde;
WITH o AS (SELECT orgnr, min(dato) AS opened FROM kunngjoring.insolvens WHERE type='Konkurs - åpning' AND dato BETWEEN '2023-09-01' AND '2024-12-31' GROUP BY 1)
SELECT 'kommune_variants' AS hva, a.postnr, count(DISTINCT a.kommune) AS n_kommune_spellings, string_agg(DISTINCT a.kommune, ' / ') AS spellings
FROM o JOIN kunngjoring.adresse a ON a.orgnr=o.orgnr AND a.dato < o.opened AND a.kilde IN ('ny','gjeldende') AND nullif(trim(a.kommune),'') IS NOT NULL
GROUP BY 2 HAVING count(DISTINCT a.kommune) > 1 ORDER BY 3 DESC LIMIT 12;
WITH o AS (SELECT orgnr, min(dato) AS opened FROM kunngjoring.insolvens WHERE type='Konkurs - åpning' AND dato BETWEEN '2023-09-01' AND '2024-12-31' GROUP BY 1),
x AS (SELECT o.orgnr, count(DISTINCT a.postnr) FILTER (WHERE a.dato >= o.opened - 730 AND a.kilde IN ('ny','gjeldende') AND nullif(trim(a.postnr),'') IS NOT NULL) AS n_postnr_24m,
             count(DISTINCT left(a.postnr,2)) FILTER (WHERE a.dato >= o.opened - 730 AND a.kilde IN ('ny','gjeldende') AND nullif(trim(a.postnr),'') IS NOT NULL) AS n_postnr2_24m
      FROM o JOIN kunngjoring.adresse a ON a.orgnr=o.orgnr AND a.dato < o.opened GROUP BY 1)
SELECT 'postnr_dist' AS hva, n_postnr_24m, n_postnr2_24m, count(*) FROM x GROUP BY 2,3 ORDER BY 2,3;
