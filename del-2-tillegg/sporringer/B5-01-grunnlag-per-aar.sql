-- B5/01 Andel åpninger med feltet «Åpnet etter» per år 2021–2026 (hele korpuset, distinkte selskaper)
\echo === per_aar ===
WITH a AS (SELECT orgnr, min(dato) AS opened FROM kunngjoring.insolvens
           WHERE type='Konkurs - åpning' AND dato >= DATE '2021-01-01' AND dato <= DATE '2026-08-24' GROUP BY 1),
f AS (SELECT a.orgnr, a.opened,
             EXISTS (SELECT 1 FROM kunngjoring.felt x WHERE x.orgnr=a.orgnr AND x.dato=a.opened
                       AND x.kunngj_type='Konkurs - åpning' AND x.felt='Åpnet etter') AS oppbud
      FROM a)
SELECT extract(year FROM opened)::int AS aar, count(*) AS n,
       count(*) FILTER (WHERE oppbud) AS n_oppbud
FROM f GROUP BY 1 ORDER BY 1;
\echo === pooled_2019_2022 ===
WITH a AS (SELECT orgnr, min(dato) AS opened FROM kunngjoring.insolvens
           WHERE type='Konkurs - åpning' AND dato >= DATE '2019-01-01' AND dato <= DATE '2022-12-31' GROUP BY 1),
f AS (SELECT a.orgnr, a.opened,
             EXISTS (SELECT 1 FROM kunngjoring.felt x WHERE x.orgnr=a.orgnr AND x.dato=a.opened
                       AND x.kunngj_type='Konkurs - åpning' AND x.felt='Åpnet etter') AS oppbud FROM a)
SELECT '2019-2022' AS periode, count(*) AS n, count(*) FILTER (WHERE oppbud) AS n_oppbud FROM f;
\echo === kohort_2023_09_2024_12 ===
WITH a AS (SELECT orgnr, min(dato) AS opened FROM kunngjoring.insolvens
           WHERE type='Konkurs - åpning' AND dato BETWEEN '2023-09-01' AND '2024-12-31' GROUP BY 1),
f AS (SELECT a.orgnr, a.opened,
             EXISTS (SELECT 1 FROM kunngjoring.felt x WHERE x.orgnr=a.orgnr AND x.dato=a.opened
                       AND x.kunngj_type='Konkurs - åpning' AND x.felt='Åpnet etter') AS oppbud FROM a)
SELECT 'kohort' AS periode, count(*) AS n, count(*) FILTER (WHERE oppbud) AS n_oppbud FROM f;
\echo === per_halvaar ===
WITH a AS (SELECT orgnr, min(dato) AS opened FROM kunngjoring.insolvens
           WHERE type='Konkurs - åpning' AND dato >= DATE '2022-07-01' AND dato <= DATE '2026-08-24' GROUP BY 1),
f AS (SELECT a.orgnr, a.opened,
             EXISTS (SELECT 1 FROM kunngjoring.felt x WHERE x.orgnr=a.orgnr AND x.dato=a.opened
                       AND x.kunngj_type='Konkurs - åpning' AND x.felt='Åpnet etter') AS oppbud FROM a)
SELECT to_char(date_trunc('quarter',opened),'YYYY"K"Q') AS kvartal, count(*) AS n,
       count(*) FILTER (WHERE oppbud) AS n_oppbud
FROM f GROUP BY 1 ORDER BY 1;
