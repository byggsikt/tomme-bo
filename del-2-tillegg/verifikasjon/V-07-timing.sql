-- V/07 Tid til innstilling etter grunnlag, faste horisonter (verifier). Alle 5 165 har >= 601 d oppfølging; 730 d på delkohort åpnet <= 2024-08-24.
WITH o AS (SELECT orgnr, min(dato) AS opened FROM kunngjoring.insolvens WHERE type='Konkurs - åpning' AND dato BETWEEN '2023-09-01' AND '2024-12-31' GROUP BY 1),
e AS (SELECT i.orgnr, min(i.dato) FILTER (WHERE i.type='Konkurs - innstilling av bobehandlingen') AS innstilt, min(i.dato) FILTER (WHERE i.type='Konkurs - avslutning av bobehandlingen') AS avsluttet FROM kunngjoring.insolvens i JOIN o USING (orgnr) WHERE i.dato >= o.opened AND i.dato <= DATE '2026-08-24' GROUP BY 1),
c AS (SELECT o.orgnr, o.opened, e.innstilt, e.avsluttet,
        CASE WHEN e.innstilt IS NOT NULL THEN 'innstilt' WHEN e.avsluttet IS NOT NULL THEN 'avsluttet' ELSE 'aapen' END AS utfall,
        (e.innstilt - o.opened) AS t_inn, (e.avsluttet - o.opened) AS t_avs,
        (DATE '2026-08-24' - o.opened) AS fu,
        EXISTS (SELECT 1 FROM kunngjoring.felt x WHERE x.orgnr=o.orgnr AND x.dato=o.opened AND x.kunngj_type='Konkurs - åpning' AND x.felt='Åpnet etter') AS oppbud
      FROM o LEFT JOIN e USING (orgnr)),
g AS (SELECT 'alle' AS gruppe, * FROM c UNION ALL SELECT CASE WHEN oppbud THEN 'oppbud' ELSE 'ingen_felt' END, * FROM c),
h AS (SELECT * FROM (VALUES (91),(183),(274),(365),(548),(601)) v(d))
SELECT 'horisont' AS hva, g.gruppe, h.d::text AS dager, count(*)::text AS n,
       count(*) FILTER (WHERE t_inn IS NOT NULL AND t_inn <= h.d)::text AS innstilt_innen,
       round(100.0*count(*) FILTER (WHERE t_inn IS NOT NULL AND t_inn <= h.d)/count(*),1)::text AS pct_innstilt,
       count(*) FILTER (WHERE t_inn IS NULL AND t_avs IS NOT NULL AND t_avs <= h.d)::text AS avsluttet_innen,
       min(fu)::text AS min_oppfolging
FROM g CROSS JOIN h GROUP BY 2,3
UNION ALL
SELECT '730_delkohort', gruppe, '730', count(*)::text,
       count(*) FILTER (WHERE t_inn IS NOT NULL AND t_inn <= 730)::text,
       round(100.0*count(*) FILTER (WHERE t_inn IS NOT NULL AND t_inn <= 730)/count(*),1)::text,
       count(*) FILTER (WHERE t_inn IS NULL AND t_avs IS NOT NULL AND t_avs <= 730)::text,
       min(fu)::text
FROM g WHERE opened <= DATE '2024-08-24' GROUP BY 2
UNION ALL
SELECT 'asof', gruppe, 'asof', count(*)::text, count(*) FILTER (WHERE utfall='innstilt')::text, round(100.0*count(*) FILTER (WHERE utfall='innstilt')/count(*),1)::text, count(*) FILTER (WHERE utfall='avsluttet')::text, count(*) FILTER (WHERE utfall='aapen')::text
FROM g GROUP BY 2
UNION ALL
SELECT 'median_t_innstilt', gruppe, 'blant innstilte', count(*) FILTER (WHERE t_inn IS NOT NULL)::text,
       percentile_disc(0.5) WITHIN GROUP (ORDER BY t_inn)::text, percentile_disc(0.25) WITHIN GROUP (ORDER BY t_inn)::text || '/' || percentile_disc(0.75) WITHIN GROUP (ORDER BY t_inn)::text || '/' || percentile_disc(0.9) WITHIN GROUP (ORDER BY t_inn)::text,
       'median_t_avsluttet=' || (percentile_disc(0.5) WITHIN GROUP (ORDER BY t_avs) FILTER (WHERE t_inn IS NULL))::text, NULL
FROM g GROUP BY 2
UNION ALL
SELECT 'crossing_check', gruppe, 'innstilt 12m/18m', count(*)::text, count(*) FILTER (WHERE t_inn <= 365)::text, count(*) FILTER (WHERE t_inn <= 548)::text, NULL, NULL FROM g GROUP BY 2
ORDER BY 1,2,3;
