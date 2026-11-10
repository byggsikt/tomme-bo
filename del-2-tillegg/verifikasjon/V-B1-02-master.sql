-- V-B1-02: independent master extract, one row per cohort company. READ-ONLY.
-- Cohort exactly as specified: first observed «Konkurs - åpning» per orgnr 2023-09-01..2024-12-31.
-- Outcome: innstilt if any «innstilling» on/after opening and <= 2026-08-24; else avsluttet; else open.
-- Basis: felt «Åpnet etter» on the opening announcement -> oppbud; absent -> ikke_oppbud.
-- bransje newlines encoded as <<NL>> so the TSV stays one row per company.
WITH o AS (
  SELECT orgnr, min(dato) AS opened
    FROM kunngjoring.insolvens
   WHERE type='Konkurs - åpning' AND dato BETWEEN '2023-09-01' AND '2024-12-31'
   GROUP BY 1),
e AS (
  SELECT i.orgnr,
         min(i.dato) FILTER (WHERE i.type='Konkurs - innstilling av bobehandlingen') AS innstilt,
         min(i.dato) FILTER (WHERE i.type='Konkurs - avslutning av bobehandlingen')  AS avsluttet
    FROM kunngjoring.insolvens i JOIN o USING (orgnr)
   WHERE i.dato >= o.opened AND i.dato <= DATE '2026-08-24'
   GROUP BY 1),
a AS (
  SELECT i.orgnr,
         max(nullif(trim(i.tingrett),'')) AS tingrett,
         max(nullif(replace(replace(i.bransje,E'\r',''),E'\n','<<NL>>'),'')) AS bransje
    FROM kunngjoring.insolvens i JOIN o ON o.orgnr=i.orgnr AND i.dato=o.opened
   WHERE i.type='Konkurs - åpning'
   GROUP BY 1)
SELECT trim(o.orgnr) AS orgnr, o.opened,
       coalesce(e.innstilt::text,'')  AS innstilt,
       coalesce(e.avsluttet::text,'') AS avsluttet,
       CASE WHEN EXISTS (SELECT 1 FROM kunngjoring.felt x
                          WHERE x.orgnr=o.orgnr AND x.dato=o.opened
                            AND x.kunngj_type='Konkurs - åpning' AND x.felt='Åpnet etter')
            THEN 'oppbud' ELSE 'ikke_oppbud' END AS basis,
       coalesce(a.tingrett,'') AS tingrett,
       coalesce(a.bransje,'')  AS bransje
  FROM o LEFT JOIN e USING (orgnr) LEFT JOIN a USING (orgnr)
 ORDER BY 1;
