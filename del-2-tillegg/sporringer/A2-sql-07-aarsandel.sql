-- A2/07 Andel åpninger med «Åpnet etter» per år, HELE korpuset (ikke bare kohorten).
-- Teller selskaper (distinct orgnr, første åpning i året), ikke rader (L8).
WITH a AS (
  SELECT orgnr, min(dato) AS opened FROM kunngjoring.insolvens
  WHERE type='Konkurs - åpning' GROUP BY 1)
SELECT extract(year FROM opened)::int AS aar,
       count(*) AS n_aapninger,
       count(*) FILTER (WHERE EXISTS (SELECT 1 FROM kunngjoring.felt x
           WHERE x.orgnr=a.orgnr AND x.dato=a.opened
             AND x.kunngj_type='Konkurs - åpning' AND x.felt='Åpnet etter')) AS n_oppbud,
       round(100.0*count(*) FILTER (WHERE EXISTS (SELECT 1 FROM kunngjoring.felt x
           WHERE x.orgnr=a.orgnr AND x.dato=a.opened
             AND x.kunngj_type='Konkurs - åpning' AND x.felt='Åpnet etter'))/count(*),1) AS pct_oppbud
FROM a GROUP BY 1 ORDER BY 1;
