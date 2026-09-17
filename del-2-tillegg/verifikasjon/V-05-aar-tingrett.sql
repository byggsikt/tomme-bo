-- V/05 Andel åpninger med «Åpnet etter» per år (hele korpuset, distinkte selskaper, første åpning) og per tingrett i kohorten (verifier)
WITH a AS (SELECT orgnr, min(dato) AS opened FROM kunngjoring.insolvens WHERE type='Konkurs - åpning' GROUP BY 1),
f AS (SELECT a.orgnr, a.opened,
        EXISTS (SELECT 1 FROM kunngjoring.felt x WHERE x.orgnr=a.orgnr AND x.dato=a.opened AND x.kunngj_type='Konkurs - åpning' AND x.felt='Åpnet etter') AS oppbud_paa_dato,
        EXISTS (SELECT 1 FROM kunngjoring.felt x WHERE x.orgnr=a.orgnr AND x.felt='Åpnet etter') AS oppbud_noen_dato
      FROM a)
SELECT 'aar' AS hva, extract(year FROM opened)::int::text AS nokkel, count(*)::text AS n, count(*) FILTER (WHERE oppbud_paa_dato)::text AS n_oppbud, round(100.0*count(*) FILTER (WHERE oppbud_paa_dato)/count(*),1)::text AS pct, count(*) FILTER (WHERE oppbud_noen_dato)::text AS n_oppbud_noen_dato
FROM f GROUP BY 2
UNION ALL
SELECT 'periode', '2019-2022', count(*)::text, count(*) FILTER (WHERE oppbud_paa_dato)::text, round(100.0*count(*) FILTER (WHERE oppbud_paa_dato)/count(*),1)::text, count(*) FILTER (WHERE oppbud_noen_dato)::text FROM f WHERE opened BETWEEN '2019-01-01' AND '2022-12-31'
UNION ALL
SELECT 'periode', '2026-01-01..2026-08-24', count(*)::text, count(*) FILTER (WHERE oppbud_paa_dato)::text, round(100.0*count(*) FILTER (WHERE oppbud_paa_dato)/count(*),1)::text, count(*) FILTER (WHERE oppbud_noen_dato)::text FROM f WHERE opened BETWEEN '2026-01-01' AND '2026-08-24'
UNION ALL
SELECT 'maaned_2026', to_char(opened,'YYYY-MM'), count(*)::text, count(*) FILTER (WHERE oppbud_paa_dato)::text, round(100.0*count(*) FILTER (WHERE oppbud_paa_dato)/count(*),1)::text, NULL FROM f WHERE opened >= '2026-01-01' GROUP BY 2
ORDER BY 1,2;
-- per tingrett i kohorten
WITH o AS (SELECT orgnr, min(dato) AS opened FROM kunngjoring.insolvens WHERE type='Konkurs - åpning' AND dato BETWEEN '2023-09-01' AND '2024-12-31' GROUP BY 1),
m AS (SELECT o.orgnr, o.opened, max(nullif(trim(i.tingrett),'')) AS tingrett, count(DISTINCT nullif(trim(i.tingrett),'')) AS n_tingrett
      FROM o JOIN kunngjoring.insolvens i ON i.orgnr=o.orgnr AND i.dato=o.opened AND i.type='Konkurs - åpning' GROUP BY 1,2),
f AS (SELECT m.*, EXISTS (SELECT 1 FROM kunngjoring.felt x WHERE x.orgnr=m.orgnr AND x.dato=m.opened AND x.kunngj_type='Konkurs - åpning' AND x.felt='Åpnet etter') AS oppbud FROM m)
SELECT 'tingrett' AS hva, coalesce(regexp_replace(tingrett,'[[:space:]]+',' ','g'),'<tom>') AS nokkel, count(*)::text, count(*) FILTER (WHERE oppbud)::text, round(100.0*count(*) FILTER (WHERE oppbud)/count(*),1)::text, max(n_tingrett)::text
FROM f GROUP BY 2 ORDER BY 5 DESC;
