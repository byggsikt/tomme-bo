-- B5/04 Tid til innstilling per tingrett (kohorten). Faste horisonter, full oppfølging for alle <= 601 d.
WITH o AS (SELECT orgnr, min(dato) AS opened FROM kunngjoring.insolvens
           WHERE type='Konkurs - åpning' AND dato BETWEEN '2023-09-01' AND '2024-12-31' GROUP BY 1),
tg AS (SELECT o.orgnr, o.opened, max(nullif(trim(i.tingrett),'')) AS tingrett
       FROM o JOIN kunngjoring.insolvens i ON i.orgnr=o.orgnr AND i.dato=o.opened AND i.type='Konkurs - åpning'
       GROUP BY 1,2),
e AS (SELECT i.orgnr,
             min(i.dato) FILTER (WHERE i.type='Konkurs - innstilling av bobehandlingen') AS innstilt,
             min(i.dato) FILTER (WHERE i.type='Konkurs - avslutning av bobehandlingen')  AS avsluttet
      FROM kunngjoring.insolvens i JOIN o USING (orgnr)
      WHERE i.dato >= o.opened AND i.dato <= DATE '2026-08-24' GROUP BY 1),
b AS (SELECT o.orgnr, o.opened, tg.tingrett,
             CASE WHEN e.innstilt IS NOT NULL THEN 'innstilt'
                  WHEN e.avsluttet IS NOT NULL THEN 'avsluttet' ELSE 'aapen' END AS utfall,
             CASE WHEN e.innstilt IS NOT NULL THEN e.innstilt - o.opened
                  WHEN e.avsluttet IS NOT NULL THEN e.avsluttet - o.opened END AS t_dager,
             EXISTS (SELECT 1 FROM kunngjoring.felt x WHERE x.orgnr=o.orgnr AND x.dato=o.opened
                       AND x.kunngj_type='Konkurs - åpning' AND x.felt='Åpnet etter') AS oppbud
      FROM o LEFT JOIN e USING (orgnr) JOIN tg USING (orgnr))
SELECT 'per_tingrett' AS blokk, coalesce(tingrett,'<mangler>') AS tingrett,
       count(*)::text AS n,
       count(*) FILTER (WHERE oppbud)::text AS n_oppbud,
       count(*) FILTER (WHERE utfall='innstilt' AND t_dager <= 91)::text AS i91,
       count(*) FILTER (WHERE utfall='innstilt' AND t_dager <= 183)::text AS i183,
       count(*) FILTER (WHERE utfall='innstilt' AND t_dager <= 274)::text AS i274,
       count(*) FILTER (WHERE utfall='innstilt' AND t_dager <= 365)::text AS i365,
       count(*) FILTER (WHERE utfall='innstilt' AND t_dager <= 548)::text AS i548,
       count(*) FILTER (WHERE utfall='innstilt' AND t_dager <= 601)::text AS i601,
       count(*) FILTER (WHERE t_dager IS NULL OR t_dager > 601)::text AS uavklart601,
       count(*) FILTER (WHERE utfall='aapen')::text AS aapen_naa,
       percentile_disc(0.5) WITHIN GROUP (ORDER BY t_dager) FILTER (WHERE utfall='innstilt')::text AS median_innst
FROM b GROUP BY 2
UNION ALL
SELECT 'per_tingrett_730', coalesce(tingrett,'<mangler>'),
       count(*) FILTER (WHERE opened <= DATE '2024-08-24')::text,
       count(*) FILTER (WHERE opened <= DATE '2024-08-24' AND utfall='innstilt' AND t_dager <= 730)::text,
       '','','','','','','','',''
FROM b GROUP BY 2
ORDER BY 1, 2;
