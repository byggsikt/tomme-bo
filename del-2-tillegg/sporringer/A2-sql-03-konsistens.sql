-- A2/03 Kohort-sanity + intern konsistens: er de ANDRE feltene like godt utfylt
-- for åpninger UTEN «Åpnet etter» som for dem MED? (L5: tom streng teller som utfylt)
WITH o AS (
  SELECT orgnr, min(dato) AS opened FROM kunngjoring.insolvens
  WHERE type='Konkurs - åpning' AND dato BETWEEN '2023-09-01' AND '2024-12-31' GROUP BY 1),
e AS (
  SELECT i.orgnr,
         min(i.dato) FILTER (WHERE i.type='Konkurs - innstilling av bobehandlingen') AS innstilt,
         min(i.dato) FILTER (WHERE i.type='Konkurs - avslutning av bobehandlingen')  AS avsluttet
  FROM kunngjoring.insolvens i JOIN o USING (orgnr)
  WHERE i.dato >= o.opened AND i.dato <= DATE '2026-08-24' GROUP BY 1),
b AS (
  SELECT o.orgnr, o.opened,
         EXISTS (SELECT 1 FROM kunngjoring.felt x
                 WHERE x.orgnr=o.orgnr AND x.dato=o.opened
                   AND x.kunngj_type='Konkurs - åpning' AND x.felt='Åpnet etter') AS oppbud,
         CASE WHEN e.innstilt IS NOT NULL THEN 'innstilt'
              WHEN e.avsluttet IS NOT NULL THEN 'ordinaer'
              ELSE 'aapen' END AS utfall
  FROM o LEFT JOIN e USING (orgnr)),
ins AS (
  SELECT b.orgnr, b.oppbud,
         bool_or(nullif(trim(i.tingrett),'')  IS NOT NULL) AS har_tingrett,
         bool_or(nullif(trim(i.bostyrer),'')  IS NOT NULL) AS har_bostyrer,
         bool_or(nullif(trim(i.saksnr),'')    IS NOT NULL) AS har_saksnr,
         bool_or(i.fristdag IS NOT NULL)                   AS har_fristdag,
         bool_or(nullif(trim(i.bransje),'')   IS NOT NULL) AS har_bransje,
         bool_or(nullif(trim(i.kapital),'')   IS NOT NULL) AS har_kapital,
         count(*)                                          AS n_insolvensrader
  FROM b JOIN kunngjoring.insolvens i
    ON i.orgnr=b.orgnr AND i.dato=b.opened AND i.type='Konkurs - åpning'
  GROUP BY 1,2)
\echo == SANITY: kohort og utfall ==
SELECT 'kohort' AS m, count(*) FROM b
UNION ALL SELECT 'innstilt', count(*) FROM b WHERE utfall='innstilt'
UNION ALL SELECT 'ordinaer', count(*) FROM b WHERE utfall='ordinaer'
UNION ALL SELECT 'aapen',    count(*) FROM b WHERE utfall='aapen'
UNION ALL SELECT 'oppbud',   count(*) FROM b WHERE oppbud
UNION ALL SELECT 'ingen_felt', count(*) FROM b WHERE NOT oppbud;
\echo == KONSISTENS: insolvensfelt utfylt, oppbud vs ingen felt ==
SELECT CASE WHEN oppbud THEN 'oppbud' ELSE 'ingen_felt' END AS gruppe,
       count(*) AS n,
       round(100.0*count(*) FILTER (WHERE har_tingrett)/count(*),1) AS pct_tingrett,
       round(100.0*count(*) FILTER (WHERE har_bostyrer)/count(*),1) AS pct_bostyrer,
       round(100.0*count(*) FILTER (WHERE har_saksnr)/count(*),1)   AS pct_saksnr,
       round(100.0*count(*) FILTER (WHERE har_fristdag)/count(*),1) AS pct_fristdag,
       round(100.0*count(*) FILTER (WHERE har_bransje)/count(*),1)  AS pct_bransje,
       round(100.0*count(*) FILTER (WHERE har_kapital)/count(*),1)  AS pct_kapital,
       round(avg(n_insolvensrader),2) AS snitt_rader
FROM ins GROUP BY 1 ORDER BY 1;
