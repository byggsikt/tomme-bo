-- B5/02 Andel «Åpnet etter: Oppbud» per tingrett, alle åpninger 2023-01-01..2026-08-24
\echo === tingrett_dekning ===
WITH a AS (SELECT orgnr, min(dato) AS opened FROM kunngjoring.insolvens
           WHERE type='Konkurs - åpning' AND dato >= DATE '2023-01-01' AND dato <= DATE '2026-08-24' GROUP BY 1),
t AS (SELECT a.orgnr, a.opened,
             max(nullif(trim(i.tingrett),'')) AS tingrett
      FROM a JOIN kunngjoring.insolvens i ON i.orgnr=a.orgnr AND i.dato=a.opened AND i.type='Konkurs - åpning'
      GROUP BY 1,2)
SELECT count(*) AS n_aapninger, count(tingrett) AS n_med_tingrett,
       count(DISTINCT tingrett) AS n_domstoler FROM t;
\echo === per_tingrett ===
WITH a AS (SELECT orgnr, min(dato) AS opened FROM kunngjoring.insolvens
           WHERE type='Konkurs - åpning' AND dato >= DATE '2023-01-01' AND dato <= DATE '2026-08-24' GROUP BY 1),
t AS (SELECT a.orgnr, a.opened, max(nullif(trim(i.tingrett),'')) AS tingrett
      FROM a JOIN kunngjoring.insolvens i ON i.orgnr=a.orgnr AND i.dato=a.opened AND i.type='Konkurs - åpning'
      GROUP BY 1,2),
f AS (SELECT t.*, EXISTS (SELECT 1 FROM kunngjoring.felt x WHERE x.orgnr=t.orgnr AND x.dato=t.opened
                            AND x.kunngj_type='Konkurs - åpning' AND x.felt='Åpnet etter') AS oppbud FROM t)
SELECT coalesce(tingrett,'<mangler>') AS tingrett, count(*) AS n, count(*) FILTER (WHERE oppbud) AS n_oppbud
FROM f GROUP BY 1 ORDER BY 2 DESC;
\echo === per_tingrett_per_aar ===
WITH a AS (SELECT orgnr, min(dato) AS opened FROM kunngjoring.insolvens
           WHERE type='Konkurs - åpning' AND dato >= DATE '2023-01-01' AND dato <= DATE '2026-08-24' GROUP BY 1),
t AS (SELECT a.orgnr, a.opened, max(nullif(trim(i.tingrett),'')) AS tingrett
      FROM a JOIN kunngjoring.insolvens i ON i.orgnr=a.orgnr AND i.dato=a.opened AND i.type='Konkurs - åpning'
      GROUP BY 1,2),
f AS (SELECT t.*, EXISTS (SELECT 1 FROM kunngjoring.felt x WHERE x.orgnr=t.orgnr AND x.dato=t.opened
                            AND x.kunngj_type='Konkurs - åpning' AND x.felt='Åpnet etter') AS oppbud FROM t)
SELECT coalesce(tingrett,'<mangler>') AS tingrett, extract(year FROM opened)::int AS aar,
       count(*) AS n, count(*) FILTER (WHERE oppbud) AS n_oppbud
FROM f GROUP BY 1,2 ORDER BY 1,2;
