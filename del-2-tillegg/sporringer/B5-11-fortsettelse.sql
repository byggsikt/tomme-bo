-- B5/11 § 136-sporet: fortsettelse av bobehandling, og de innstilte uten sletting
WITH o AS (SELECT orgnr, min(dato) AS opened FROM kunngjoring.insolvens
           WHERE type='Konkurs - åpning' AND dato BETWEEN '2023-09-01' AND '2024-12-31' GROUP BY 1),
e AS (SELECT i.orgnr,
             min(i.dato) FILTER (WHERE i.type='Konkurs - innstilling av bobehandlingen') AS innstilt,
             min(i.dato) FILTER (WHERE i.type='Konkurs - avslutning av bobehandlingen')  AS avsluttet,
             min(i.dato) FILTER (WHERE i.type='Fortsettelse av bobehandling')            AS fortsettelse
      FROM kunngjoring.insolvens i JOIN o USING (orgnr)
      WHERE i.dato >= o.opened AND i.dato <= DATE '2026-08-24' GROUP BY 1)
SELECT 'fortsettelse_kohort' AS blokk,
       count(*) FILTER (WHERE e.fortsettelse IS NOT NULL) AS n_fortsettelse,
       count(*) FILTER (WHERE e.fortsettelse IS NOT NULL AND e.innstilt IS NOT NULL) AS av_disse_innstilt,
       count(*) FILTER (WHERE e.fortsettelse IS NOT NULL AND e.innstilt IS NOT NULL AND e.fortsettelse > e.innstilt) AS fortsettelse_etter_innstilling,
       count(*) FILTER (WHERE e.innstilt IS NOT NULL AND e.avsluttet IS NOT NULL) AS innstilt_og_avsluttet,
       count(*) AS n_kohort
FROM o LEFT JOIN e USING (orgnr);
\echo === fortsettelse_hele_korpuset_per_aar ===
SELECT extract(year FROM dato)::int AS aar, count(DISTINCT orgnr) AS selskaper
FROM kunngjoring.insolvens WHERE type='Fortsettelse av bobehandling' GROUP BY 1 ORDER BY 1;
\echo === retensjonsgrense_utfallstyper ===
SELECT type, min(dato) AS forste, count(*) FILTER (WHERE dato < DATE '2023-09-01') AS for_kohortstart
FROM kunngjoring.insolvens
WHERE type IN ('Konkurs - innstilling av bobehandlingen','Konkurs - avslutning av bobehandlingen','Konkurs - åpning')
GROUP BY 1;
