-- B5/03 Tid til innstilling etter åpningsgrunnlag. Faste horisonter, full oppfølging.
WITH o AS (SELECT orgnr, min(dato) AS opened FROM kunngjoring.insolvens
           WHERE type='Konkurs - åpning' AND dato BETWEEN '2023-09-01' AND '2024-12-31' GROUP BY 1),
e AS (SELECT i.orgnr,
             min(i.dato) FILTER (WHERE i.type='Konkurs - innstilling av bobehandlingen') AS innstilt,
             min(i.dato) FILTER (WHERE i.type='Konkurs - avslutning av bobehandlingen')  AS avsluttet
      FROM kunngjoring.insolvens i JOIN o USING (orgnr)
      WHERE i.dato >= o.opened AND i.dato <= DATE '2026-08-24' GROUP BY 1),
b AS (SELECT o.orgnr, o.opened, e.innstilt, e.avsluttet,
             CASE WHEN e.innstilt IS NOT NULL THEN 'innstilt'
                  WHEN e.avsluttet IS NOT NULL THEN 'avsluttet' ELSE 'aapen' END AS utfall,
             CASE WHEN e.innstilt IS NOT NULL THEN e.innstilt - o.opened
                  WHEN e.avsluttet IS NOT NULL THEN e.avsluttet - o.opened END AS t_dager,
             EXISTS (SELECT 1 FROM kunngjoring.felt x WHERE x.orgnr=o.orgnr AND x.dato=o.opened
                       AND x.kunngj_type='Konkurs - åpning' AND x.felt='Åpnet etter') AS oppbud,
             (DATE '2026-08-24' - o.opened) AS oppfolging
      FROM o LEFT JOIN e USING (orgnr))
SELECT 'sanity' AS blokk, count(*)::text AS a, count(*) FILTER (WHERE innstilt IS NOT NULL AND avsluttet IS NOT NULL AND avsluttet < innstilt)::text AS b,
       min(oppfolging)::text AS c, max(oppfolging)::text AS d, ''::text AS e, ''::text AS f, ''::text AS g, ''::text AS h
FROM b
UNION ALL
SELECT 'horisont_alle_5165', CASE WHEN oppbud THEN 'oppbud' ELSE 'ingen_felt' END,
       count(*)::text,
       count(*) FILTER (WHERE utfall='innstilt' AND t_dager <= 91)::text,
       count(*) FILTER (WHERE utfall='innstilt' AND t_dager <= 183)::text,
       count(*) FILTER (WHERE utfall='innstilt' AND t_dager <= 274)::text,
       count(*) FILTER (WHERE utfall='innstilt' AND t_dager <= 365)::text,
       count(*) FILTER (WHERE utfall='innstilt' AND t_dager <= 548)::text,
       count(*) FILTER (WHERE utfall='innstilt' AND t_dager <= 601)::text
FROM b GROUP BY 2
UNION ALL
SELECT 'horisont_alle_5165_total', 'alle', count(*)::text,
       count(*) FILTER (WHERE utfall='innstilt' AND t_dager <= 91)::text,
       count(*) FILTER (WHERE utfall='innstilt' AND t_dager <= 183)::text,
       count(*) FILTER (WHERE utfall='innstilt' AND t_dager <= 274)::text,
       count(*) FILTER (WHERE utfall='innstilt' AND t_dager <= 365)::text,
       count(*) FILTER (WHERE utfall='innstilt' AND t_dager <= 548)::text,
       count(*) FILTER (WHERE utfall='innstilt' AND t_dager <= 601)::text
FROM b
UNION ALL
SELECT 'avsluttet_ordinaert_alle_5165', CASE WHEN oppbud THEN 'oppbud' ELSE 'ingen_felt' END, count(*)::text,
       count(*) FILTER (WHERE utfall='avsluttet' AND t_dager <= 91)::text,
       count(*) FILTER (WHERE utfall='avsluttet' AND t_dager <= 183)::text,
       count(*) FILTER (WHERE utfall='avsluttet' AND t_dager <= 274)::text,
       count(*) FILTER (WHERE utfall='avsluttet' AND t_dager <= 365)::text,
       count(*) FILTER (WHERE utfall='avsluttet' AND t_dager <= 548)::text,
       count(*) FILTER (WHERE utfall='avsluttet' AND t_dager <= 601)::text
FROM b GROUP BY 2
UNION ALL
SELECT 'uavklart_alle_5165', CASE WHEN oppbud THEN 'oppbud' ELSE 'ingen_felt' END, count(*)::text,
       count(*) FILTER (WHERE t_dager IS NULL OR t_dager > 91)::text,
       count(*) FILTER (WHERE t_dager IS NULL OR t_dager > 183)::text,
       count(*) FILTER (WHERE t_dager IS NULL OR t_dager > 274)::text,
       count(*) FILTER (WHERE t_dager IS NULL OR t_dager > 365)::text,
       count(*) FILTER (WHERE t_dager IS NULL OR t_dager > 548)::text,
       count(*) FILTER (WHERE t_dager IS NULL OR t_dager > 601)::text
FROM b GROUP BY 2
UNION ALL
SELECT 'horisont_730_delkohort', CASE WHEN oppbud THEN 'oppbud' ELSE 'ingen_felt' END, count(*)::text,
       count(*) FILTER (WHERE utfall='innstilt' AND t_dager <= 730)::text,
       count(*) FILTER (WHERE utfall='avsluttet' AND t_dager <= 730)::text,
       count(*) FILTER (WHERE t_dager IS NULL OR t_dager > 730)::text,
       count(*) FILTER (WHERE utfall='innstilt' AND t_dager <= 548)::text,
       count(*) FILTER (WHERE utfall='innstilt' AND t_dager <= 365)::text, ''
FROM b WHERE opened <= DATE '2024-08-24' GROUP BY 2
UNION ALL
SELECT 'horisont_730_delkohort_total', 'alle', count(*)::text,
       count(*) FILTER (WHERE utfall='innstilt' AND t_dager <= 730)::text,
       count(*) FILTER (WHERE utfall='avsluttet' AND t_dager <= 730)::text,
       count(*) FILTER (WHERE t_dager IS NULL OR t_dager > 730)::text, '', '', ''
FROM b WHERE opened <= DATE '2024-08-24'
UNION ALL
SELECT 'kvantiler_innstilling', CASE WHEN oppbud THEN 'oppbud' ELSE 'ingen_felt' END, count(*) FILTER (WHERE utfall='innstilt')::text,
       percentile_disc(0.10) WITHIN GROUP (ORDER BY t_dager) FILTER (WHERE utfall='innstilt')::text,
       percentile_disc(0.25) WITHIN GROUP (ORDER BY t_dager) FILTER (WHERE utfall='innstilt')::text,
       percentile_disc(0.50) WITHIN GROUP (ORDER BY t_dager) FILTER (WHERE utfall='innstilt')::text,
       percentile_disc(0.75) WITHIN GROUP (ORDER BY t_dager) FILTER (WHERE utfall='innstilt')::text,
       percentile_disc(0.90) WITHIN GROUP (ORDER BY t_dager) FILTER (WHERE utfall='innstilt')::text,
       max(t_dager) FILTER (WHERE utfall='innstilt')::text
FROM b GROUP BY 2
UNION ALL
SELECT 'kvantiler_ordinaer_avslutning', CASE WHEN oppbud THEN 'oppbud' ELSE 'ingen_felt' END, count(*) FILTER (WHERE utfall='avsluttet')::text,
       percentile_disc(0.10) WITHIN GROUP (ORDER BY t_dager) FILTER (WHERE utfall='avsluttet')::text,
       percentile_disc(0.25) WITHIN GROUP (ORDER BY t_dager) FILTER (WHERE utfall='avsluttet')::text,
       percentile_disc(0.50) WITHIN GROUP (ORDER BY t_dager) FILTER (WHERE utfall='avsluttet')::text,
       percentile_disc(0.75) WITHIN GROUP (ORDER BY t_dager) FILTER (WHERE utfall='avsluttet')::text,
       percentile_disc(0.90) WITHIN GROUP (ORDER BY t_dager) FILTER (WHERE utfall='avsluttet')::text,
       max(t_dager) FILTER (WHERE utfall='avsluttet')::text
FROM b GROUP BY 2
ORDER BY 1,2;
