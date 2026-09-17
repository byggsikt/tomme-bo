-- A2/18 Er «ingen felt»-gruppen ren kreditor/stat-begjæring, eller inneholder den
-- konkurser åpnet i sporet etter tvangsoppløsning (asl. § 16-15)?
-- Ser på alle insolvens-/varseltyper før eller på åpningsdatoen.
WITH o AS (
  SELECT orgnr, min(dato) AS opened FROM kunngjoring.insolvens
  WHERE type='Konkurs - åpning' AND dato BETWEEN '2023-09-01' AND '2024-12-31' GROUP BY 1),
b AS (
  SELECT o.orgnr, o.opened,
         EXISTS (SELECT 1 FROM kunngjoring.felt x
                 WHERE x.orgnr=o.orgnr AND x.dato=o.opened
                   AND x.kunngj_type='Konkurs - åpning' AND x.felt='Åpnet etter') AS oppbud,
         EXISTS (SELECT 1 FROM kunngjoring.kunngjoring k
                 WHERE k.orgnr=o.orgnr AND k.dato <= o.opened
                   AND k.type ILIKE '%tvangsoppl%') AS varsel_tvang,
         EXISTS (SELECT 1 FROM kunngjoring.kunngjoring k
                 WHERE k.orgnr=o.orgnr AND k.dato <= o.opened
                   AND (k.type ILIKE 'Tvangsavvikling%' OR k.type ILIKE 'Tvangsoppløsning%')) AS vedtak_tvang
  FROM o)
SELECT CASE WHEN oppbud THEN 'oppbud' ELSE 'ingen_felt' END AS gruppe,
       count(*) AS n,
       count(*) FILTER (WHERE varsel_tvang) AS n_varsel_tvang,
       round(100.0*count(*) FILTER (WHERE varsel_tvang)/count(*),1) AS pct_varsel,
       count(*) FILTER (WHERE vedtak_tvang) AS n_vedtak_tvang,
       round(100.0*count(*) FILTER (WHERE vedtak_tvang)/count(*),1) AS pct_vedtak
FROM b GROUP BY 1 ORDER BY 1;
