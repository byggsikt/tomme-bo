-- A2/04 Er insolvensfeltene like godt utfylt uten «Åpnet etter» som med?
WITH o AS (
  SELECT orgnr, min(dato) AS opened FROM kunngjoring.insolvens
  WHERE type='Konkurs - åpning' AND dato BETWEEN '2023-09-01' AND '2024-12-31' GROUP BY 1),
b AS (
  SELECT o.orgnr, o.opened,
         EXISTS (SELECT 1 FROM kunngjoring.felt x
                 WHERE x.orgnr=o.orgnr AND x.dato=o.opened
                   AND x.kunngj_type='Konkurs - åpning' AND x.felt='Åpnet etter') AS oppbud
  FROM o),
ins AS (
  SELECT b.orgnr, b.oppbud,
         bool_or(nullif(trim(i.tingrett),'')  IS NOT NULL) AS har_tingrett,
         bool_or(nullif(trim(i.bostyrer),'')  IS NOT NULL) AS har_bostyrer,
         bool_or(nullif(trim(i.saksnr),'')    IS NOT NULL) AS har_saksnr,
         bool_or(i.fristdag IS NOT NULL)                   AS har_fristdag,
         bool_or(nullif(trim(i.bransje),'')   IS NOT NULL) AS har_bransje,
         bool_or(nullif(trim(i.kapital),'')   IS NOT NULL) AS har_kapital,
         count(*)                                          AS n_rader
  FROM b LEFT JOIN kunngjoring.insolvens i
    ON i.orgnr=b.orgnr AND i.dato=b.opened AND i.type='Konkurs - åpning'
  GROUP BY 1,2)
SELECT CASE WHEN oppbud THEN 'oppbud' ELSE 'ingen_felt' END AS gruppe,
       count(*) AS n,
       count(*) FILTER (WHERE har_tingrett) AS n_tingrett,
       round(100.0*count(*) FILTER (WHERE har_tingrett)/count(*),1) AS pct_tingrett,
       count(*) FILTER (WHERE har_bostyrer) AS n_bostyrer,
       round(100.0*count(*) FILTER (WHERE har_bostyrer)/count(*),1) AS pct_bostyrer,
       count(*) FILTER (WHERE har_saksnr) AS n_saksnr,
       round(100.0*count(*) FILTER (WHERE har_saksnr)/count(*),1)   AS pct_saksnr,
       count(*) FILTER (WHERE har_fristdag) AS n_fristdag,
       round(100.0*count(*) FILTER (WHERE har_fristdag)/count(*),1) AS pct_fristdag,
       count(*) FILTER (WHERE har_bransje) AS n_bransje,
       round(100.0*count(*) FILTER (WHERE har_bransje)/count(*),1)  AS pct_bransje,
       count(*) FILTER (WHERE har_kapital) AS n_kapital,
       round(100.0*count(*) FILTER (WHERE har_kapital)/count(*),1)  AS pct_kapital,
       round(avg(n_rader),2) AS snitt_insolvensrader
FROM ins GROUP BY 1 ORDER BY 1;
