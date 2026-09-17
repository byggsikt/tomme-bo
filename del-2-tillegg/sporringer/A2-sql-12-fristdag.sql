-- A2/12 UAVHENGIG PROSESSTEST: fristdagen (kkl. § 1-2) er dagen begjæringen kom
-- inn til retten. Ved oppbud åpnes boet nesten samtidig; en kreditorbegjæring
-- krever innkalling og rettsmøte og gir et lengre gap. Hvis gruppen UTEN feltet
-- virkelig er begjæringer, må gapet være systematisk lengre.
WITH o AS (
  SELECT orgnr, min(dato) AS opened FROM kunngjoring.insolvens
  WHERE type='Konkurs - åpning' AND dato BETWEEN '2023-09-01' AND '2024-12-31' GROUP BY 1),
b AS (
  SELECT o.orgnr, o.opened,
         (SELECT max(i.fristdag) FROM kunngjoring.insolvens i
            WHERE i.orgnr=o.orgnr AND i.dato=o.opened AND i.type='Konkurs - åpning') AS fristdag,
         EXISTS (SELECT 1 FROM kunngjoring.felt x
                 WHERE x.orgnr=o.orgnr AND x.dato=o.opened
                   AND x.kunngj_type='Konkurs - åpning' AND x.felt='Åpnet etter') AS oppbud
  FROM o),
g AS (SELECT *, (opened - fristdag) AS gap FROM b WHERE fristdag IS NOT NULL)
SELECT CASE WHEN oppbud THEN 'oppbud' ELSE 'ingen_felt' END AS gruppe,
       count(*) AS n,
       round(100.0*count(*) FILTER (WHERE gap <= 14)/count(*),1) AS pct_gap_0_14d,
       round(100.0*count(*) FILTER (WHERE gap BETWEEN 15 AND 60)/count(*),1) AS pct_gap_15_60d,
       round(100.0*count(*) FILTER (WHERE gap > 60)/count(*),1) AS pct_gap_over60d,
       percentile_disc(0.25) WITHIN GROUP (ORDER BY gap) AS p25,
       percentile_disc(0.50) WITHIN GROUP (ORDER BY gap) AS median,
       percentile_disc(0.75) WITHIN GROUP (ORDER BY gap) AS p75,
       percentile_disc(0.90) WITHIN GROUP (ORDER BY gap) AS p90
FROM g GROUP BY 1 ORDER BY 1;
