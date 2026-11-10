-- B1 master extract: one row per cohort company (5 165), read-only.
-- Cohort = first observed «Konkurs - åpning» per orgnr in 2023-09-01..2024-12-31 (identical to the study).
-- Outcome events: first innstilling / first avslutning on/after opening and <= 2026-08-24.
-- Basis: felt «Åpnet etter» on the opening announcement (only value ever printed: «Oppbud») -> oppbud; absent -> not registered as oppbud (petition by others).
-- Opening-row attributes (tingrett, bransje, saksnr, fristdag) from kunngjoring.insolvens on the opening date.
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
         max(nullif(trim(i.tingrett),''))                                   AS tingrett,
         max(replace(replace(i.bransje, E'\r', ''), E'\n', ' \n '))       AS bransje,
         max(nullif(trim(i.saksnr),''))                                     AS saksnr,
         max(i.fristdag)                                                    AS fristdag,
         count(*)                                                           AS apningsrader
  FROM kunngjoring.insolvens i JOIN o ON o.orgnr=i.orgnr AND i.dato=o.opened
  WHERE i.type='Konkurs - åpning'
  GROUP BY 1)
SELECT o.orgnr, o.opened, e.innstilt, e.avsluttet,
       CASE WHEN EXISTS (SELECT 1 FROM kunngjoring.felt x
                         WHERE x.orgnr=o.orgnr AND x.dato=o.opened
                           AND x.kunngj_type='Konkurs - åpning' AND x.felt='Åpnet etter')
            THEN 1 ELSE 0 END AS oppbud,
       a.tingrett, a.bransje, a.saksnr, a.fristdag, a.apningsrader
FROM o LEFT JOIN e USING (orgnr) LEFT JOIN a USING (orgnr)
ORDER BY o.orgnr;
