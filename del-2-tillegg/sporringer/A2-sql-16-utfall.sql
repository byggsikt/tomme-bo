-- A2/16 Utfall etter grunnlag — reproduserer funn (b) og gir tellere/nevnere
WITH o AS (
  SELECT orgnr, min(dato) AS opened FROM kunngjoring.insolvens
  WHERE type='Konkurs - åpning' AND dato BETWEEN '2023-09-01' AND '2024-12-31' GROUP BY 1),
e AS (
  SELECT i.orgnr,
         min(i.dato) FILTER (WHERE i.type='Konkurs - innstilling av bobehandlingen') AS innstilt,
         min(i.dato) FILTER (WHERE i.type='Konkurs - avslutning av bobehandlingen')  AS avsluttet
  FROM kunngjoring.insolvens i JOIN o USING (orgnr)
  WHERE i.dato >= o.opened AND i.dato <= DATE '2026-08-24' GROUP BY 1),
b AS (
  SELECT o.orgnr, o.opened, e.innstilt, e.avsluttet,
         EXISTS (SELECT 1 FROM kunngjoring.felt x
                 WHERE x.orgnr=o.orgnr AND x.dato=o.opened
                   AND x.kunngj_type='Konkurs - åpning' AND x.felt='Åpnet etter') AS oppbud
  FROM o LEFT JOIN e USING (orgnr))
SELECT CASE WHEN oppbud THEN 'oppbud' ELSE 'ingen_felt' END AS gruppe,
       'as-of 24.08.2026' AS vindu,
       count(*) AS n,
       count(*) FILTER (WHERE innstilt IS NOT NULL) AS n_innstilt,
       round(100.0*count(*) FILTER (WHERE innstilt IS NOT NULL)/count(*),1) AS pct_innstilt,
       percentile_disc(0.5) WITHIN GROUP (ORDER BY (innstilt - opened)) FILTER (WHERE innstilt IS NOT NULL) AS median_dager
FROM b GROUP BY 1
UNION ALL
SELECT CASE WHEN oppbud THEN 'oppbud' ELSE 'ingen_felt' END,
       '730d fast vindu (åpnet <= 2024-08-24)',
       count(*),
       count(*) FILTER (WHERE innstilt IS NOT NULL AND innstilt - opened <= 730),
       round(100.0*count(*) FILTER (WHERE innstilt IS NOT NULL AND innstilt - opened <= 730)/count(*),1),
       percentile_disc(0.5) WITHIN GROUP (ORDER BY (innstilt - opened)) FILTER (WHERE innstilt IS NOT NULL AND innstilt - opened <= 730)
FROM b WHERE opened <= DATE '2024-08-24' GROUP BY 1
ORDER BY 2,1;
