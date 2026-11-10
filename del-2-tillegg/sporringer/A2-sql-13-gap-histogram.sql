-- A2/13 Finere fordeling av fristdag→åpning, for å anslå hvor mye overlapp
-- (= mulig feilklassifisering) det er mellom gruppene.
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
g AS (SELECT *, (opened - fristdag) AS gap FROM b WHERE fristdag IS NOT NULL),
bk AS (SELECT oppbud, CASE
          WHEN gap < 0 THEN 'a_negativ'
          WHEN gap = 0 THEN 'b_0d'
          WHEN gap BETWEEN 1 AND 2 THEN 'c_1-2d'
          WHEN gap BETWEEN 3 AND 7 THEN 'd_3-7d'
          WHEN gap BETWEEN 8 AND 14 THEN 'e_8-14d'
          WHEN gap BETWEEN 15 AND 30 THEN 'f_15-30d'
          WHEN gap BETWEEN 31 AND 60 THEN 'g_31-60d'
          WHEN gap BETWEEN 61 AND 180 THEN 'h_61-180d'
          ELSE 'i_over180d' END AS bucket FROM g)
SELECT bucket,
       count(*) FILTER (WHERE oppbud) AS n_oppbud,
       round(100.0*count(*) FILTER (WHERE oppbud)/3734.0,1) AS pct_oppbud,
       count(*) FILTER (WHERE NOT oppbud) AS n_ingen,
       round(100.0*count(*) FILTER (WHERE NOT oppbud)/1431.0,1) AS pct_ingen
FROM bk GROUP BY 1 ORDER BY 1;
