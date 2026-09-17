-- A2/20 KONTROLL: «Konkurs åpnet» (rettens beslutningsdato) vs dato (kunngjøringsdato).
-- Samme publiseringsrutine for begge grupper => samme lag. Hvis gruppen uten
-- feltet var en annen publiseringsstrøm, ville laget skilt seg.
WITH o AS (
  SELECT orgnr, min(dato) AS opened FROM kunngjoring.insolvens
  WHERE type='Konkurs - åpning' AND dato BETWEEN '2023-09-01' AND '2024-12-31' GROUP BY 1),
b AS (
  SELECT o.orgnr, o.opened,
         EXISTS (SELECT 1 FROM kunngjoring.felt x
                 WHERE x.orgnr=o.orgnr AND x.dato=o.opened
                   AND x.kunngj_type='Konkurs - åpning' AND x.felt='Åpnet etter') AS oppbud,
         (SELECT to_date(substring(max(x.verdi) from '\d{2}\.\d{2}\.\d{4}'),'DD.MM.YYYY')
            FROM kunngjoring.felt x
           WHERE x.orgnr=o.orgnr AND x.dato=o.opened
             AND x.kunngj_type='Konkurs - åpning' AND x.felt='Konkurs åpnet') AS beslutning
  FROM o)
SELECT CASE WHEN oppbud THEN 'oppbud' ELSE 'ingen_felt' END AS gruppe,
       count(*) AS n,
       count(beslutning) AS n_m_beslutning,
       percentile_disc(0.5) WITHIN GROUP (ORDER BY (opened - beslutning)) AS median_lag_dager,
       percentile_disc(0.9) WITHIN GROUP (ORDER BY (opened - beslutning)) AS p90_lag_dager,
       round(100.0*count(*) FILTER (WHERE opened - beslutning BETWEEN 0 AND 7)/count(beslutning),1) AS pct_lag_0_7d
FROM b GROUP BY 1 ORDER BY 1;
