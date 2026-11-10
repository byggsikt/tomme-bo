-- B5/10 Er de 351 levende bo eller tapte kunngjøringer? Hendelser ETTER åpningen, per utfall.
WITH o AS (SELECT orgnr, min(dato) AS opened FROM kunngjoring.insolvens
           WHERE type='Konkurs - åpning' AND dato BETWEEN '2023-09-01' AND '2024-12-31' GROUP BY 1),
e AS (SELECT i.orgnr,
             min(i.dato) FILTER (WHERE i.type='Konkurs - innstilling av bobehandlingen') AS innstilt,
             min(i.dato) FILTER (WHERE i.type='Konkurs - avslutning av bobehandlingen')  AS avsluttet
      FROM kunngjoring.insolvens i JOIN o USING (orgnr)
      WHERE i.dato >= o.opened AND i.dato <= DATE '2026-08-24' GROUP BY 1),
b AS (SELECT o.orgnr, o.opened,
             CASE WHEN e.innstilt IS NOT NULL THEN 'innstilt'
                  WHEN e.avsluttet IS NOT NULL THEN 'avsluttet' ELSE 'aapen' END AS utfall
      FROM o LEFT JOIN e USING (orgnr)),
ev AS (SELECT b.orgnr, b.utfall, v.type_kanon, v.dato
       FROM b JOIN kunngjoring.v_hendelse v ON v.orgnr=b.orgnr
       WHERE v.dato > b.opened AND v.dato <= DATE '2026-08-24')
\echo === etterhendelser_per_utfall ===
SELECT utfall, type_kanon, count(DISTINCT orgnr) AS selskaper FROM ev
GROUP BY 1,2 HAVING count(DISTINCT orgnr) >= 5 ORDER BY 1, 3 DESC;
\echo === andel_med_noen_etterhendelse ===
WITH o AS (SELECT orgnr, min(dato) AS opened FROM kunngjoring.insolvens
           WHERE type='Konkurs - åpning' AND dato BETWEEN '2023-09-01' AND '2024-12-31' GROUP BY 1),
e AS (SELECT i.orgnr,
             min(i.dato) FILTER (WHERE i.type='Konkurs - innstilling av bobehandlingen') AS innstilt,
             min(i.dato) FILTER (WHERE i.type='Konkurs - avslutning av bobehandlingen')  AS avsluttet
      FROM kunngjoring.insolvens i JOIN o USING (orgnr)
      WHERE i.dato >= o.opened AND i.dato <= DATE '2026-08-24' GROUP BY 1),
b AS (SELECT o.orgnr, o.opened,
             CASE WHEN e.innstilt IS NOT NULL THEN 'innstilt'
                  WHEN e.avsluttet IS NOT NULL THEN 'avsluttet' ELSE 'aapen' END AS utfall
      FROM o LEFT JOIN e USING (orgnr))
SELECT b.utfall, count(*) AS n,
       count(*) FILTER (WHERE EXISTS (SELECT 1 FROM kunngjoring.v_hendelse v WHERE v.orgnr=b.orgnr
                                        AND v.dato > b.opened AND v.dato <= DATE '2026-08-24')) AS har_etterhendelse,
       count(*) FILTER (WHERE EXISTS (SELECT 1 FROM kunngjoring.v_hendelse v WHERE v.orgnr=b.orgnr
                                        AND v.dato > b.opened + 365 AND v.dato <= DATE '2026-08-24')) AS etter_365d,
       count(*) FILTER (WHERE EXISTS (SELECT 1 FROM kunngjoring.kunngjoring k WHERE k.orgnr=b.orgnr
                                        AND k.dato > b.opened AND k.dato <= DATE '2026-08-24'
                                        AND k.type ILIKE '%slett%')) AS er_slettet
FROM b GROUP BY 1 ORDER BY 1;
\echo === insolvenstyper_hele_korpuset ===
SELECT type, count(*) AS rader, count(DISTINCT orgnr) AS selskaper, min(dato) AS forst, max(dato) AS sist
FROM kunngjoring.insolvens GROUP BY 1 ORDER BY 3 DESC LIMIT 25;
