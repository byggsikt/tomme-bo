-- V/06 Konsistenskontrollene A2 bygger på (verifier)
WITH o AS (SELECT orgnr, min(dato) AS opened FROM kunngjoring.insolvens WHERE type='Konkurs - åpning' AND dato BETWEEN '2023-09-01' AND '2024-12-31' GROUP BY 1),
c AS (SELECT o.orgnr, o.opened,
        EXISTS (SELECT 1 FROM kunngjoring.felt x WHERE x.orgnr=o.orgnr AND x.dato=o.opened AND x.kunngj_type='Konkurs - åpning' AND x.felt='Åpnet etter') AS oppbud,
        EXISTS (SELECT 1 FROM kunngjoring.felt x WHERE x.orgnr=o.orgnr AND x.felt='Åpnet etter') AS oppbud_noen_dato,
        (SELECT count(DISTINCT i.dato) FROM kunngjoring.insolvens i WHERE i.orgnr=o.orgnr AND i.type='Konkurs - åpning') AS n_aapningsdatoer,
        (SELECT max(i.fristdag) FROM kunngjoring.insolvens i WHERE i.orgnr=o.orgnr AND i.dato=o.opened AND i.type='Konkurs - åpning') AS fristdag,
        (SELECT count(*) FROM kunngjoring.insolvens i WHERE i.orgnr=o.orgnr AND i.dato=o.opened AND i.type='Konkurs - åpning' AND nullif(trim(i.tingrett),'') IS NOT NULL) AS har_tingrett,
        (SELECT count(*) FROM kunngjoring.insolvens i WHERE i.orgnr=o.orgnr AND i.dato=o.opened AND i.type='Konkurs - åpning' AND nullif(trim(i.bostyrer),'') IS NOT NULL) AS har_bostyrer,
        (SELECT count(*) FROM kunngjoring.insolvens i WHERE i.orgnr=o.orgnr AND i.dato=o.opened AND i.type='Konkurs - åpning' AND nullif(trim(i.saksnr),'') IS NOT NULL) AS har_saksnr,
        (SELECT count(*) FROM kunngjoring.insolvens i WHERE i.orgnr=o.orgnr AND i.dato=o.opened AND i.type='Konkurs - åpning' AND nullif(trim(i.bransje),'') IS NOT NULL) AS har_bransje,
        (SELECT max(x.verdi) FROM kunngjoring.felt x WHERE x.orgnr=o.orgnr AND x.dato=o.opened AND x.kunngj_type='Konkurs - åpning' AND x.felt='Konkurs åpnet') AS aapnet_verdi,
        (SELECT string_agg(DISTINCT coalesce(k.register,'<NULL>'), '+') FROM kunngjoring.kunngjoring k WHERE k.orgnr=o.orgnr AND k.dato=o.opened AND k.type_kanon='Konkurs - åpning') AS registre
      FROM o)
-- (a) feltinventar per gruppe
SELECT 'a_feltinventar' AS hva, CASE WHEN c.oppbud THEN 'oppbud' ELSE 'ingen_felt' END AS gruppe, x.felt AS nokkel, count(DISTINCT c.orgnr)::text AS n, NULL AS v1, NULL AS v2
FROM c JOIN kunngjoring.felt x ON x.orgnr=c.orgnr AND x.dato=c.opened AND x.kunngj_type='Konkurs - åpning'
GROUP BY 2,3
UNION ALL
-- (b) gruppetall: feltet på noen dato, antall åpningsdatoer, insolvensfelt, registre
SELECT 'b_gruppe', CASE WHEN oppbud THEN 'oppbud' ELSE 'ingen_felt' END, 'n=' || count(*)::text,
       'noen_dato=' || count(*) FILTER (WHERE oppbud_noen_dato)::text || ' flere_aapningsdatoer=' || count(*) FILTER (WHERE n_aapningsdatoer > 1)::text,
       'tingrett=' || count(*) FILTER (WHERE har_tingrett>0)::text || ' bostyrer=' || count(*) FILTER (WHERE har_bostyrer>0)::text || ' saksnr=' || count(*) FILTER (WHERE har_saksnr>0)::text || ' fristdag=' || count(*) FILTER (WHERE fristdag IS NOT NULL)::text || ' bransje=' || count(*) FILTER (WHERE har_bransje>0)::text || ' aapnetverdi=' || count(*) FILTER (WHERE aapnet_verdi IS NOT NULL)::text,
       NULL
FROM c GROUP BY 2
UNION ALL
SELECT 'b2_registre', CASE WHEN oppbud THEN 'oppbud' ELSE 'ingen_felt' END, coalesce(registre,'<ingen rad>'), count(*)::text, NULL, NULL FROM c GROUP BY 2,3
UNION ALL
-- (c) fristdagsgap-histogram
SELECT 'c_gap', CASE WHEN oppbud THEN 'oppbud' ELSE 'ingen_felt' END,
       CASE WHEN (opened-fristdag) < 0 THEN '0_negativ' WHEN (opened-fristdag)=0 THEN '1_0d' WHEN (opened-fristdag) BETWEEN 1 AND 2 THEN '2_1-2d' WHEN (opened-fristdag) BETWEEN 3 AND 7 THEN '3_3-7d' WHEN (opened-fristdag) BETWEEN 8 AND 14 THEN '4_8-14d' WHEN (opened-fristdag) BETWEEN 15 AND 30 THEN '5_15-30d' WHEN (opened-fristdag) BETWEEN 31 AND 60 THEN '6_31-60d' WHEN (opened-fristdag) BETWEEN 61 AND 180 THEN '7_61-180d' ELSE '8_over180d' END,
       count(*)::text, NULL, NULL
FROM c WHERE fristdag IS NOT NULL GROUP BY 2,3
UNION ALL
-- (d) gap-kvantiler og tak på parsertap
SELECT 'd_gapkvantiler', CASE WHEN oppbud THEN 'oppbud' ELSE 'ingen_felt' END,
       'median=' || percentile_disc(0.5) WITHIN GROUP (ORDER BY opened-fristdag)::text || ' p25=' || percentile_disc(0.25) WITHIN GROUP (ORDER BY opened-fristdag)::text || ' p75=' || percentile_disc(0.75) WITHIN GROUP (ORDER BY opened-fristdag)::text || ' p90=' || percentile_disc(0.9) WITHIN GROUP (ORDER BY opened-fristdag)::text,
       'gap<=7d=' || count(*) FILTER (WHERE opened-fristdag <= 7)::text || ' gap<=2d=' || count(*) FILTER (WHERE opened-fristdag <= 2)::text || ' gap=0=' || count(*) FILTER (WHERE opened-fristdag = 0)::text || ' gap>14d=' || count(*) FILTER (WHERE opened-fristdag > 14)::text,
       'n=' || count(*)::text, NULL
FROM c WHERE fristdag IS NOT NULL GROUP BY 2
UNION ALL
-- (e) publiseringslag: dato − «Konkurs åpnet»
SELECT 'e_publag', CASE WHEN oppbud THEN 'oppbud' ELSE 'ingen_felt' END,
       'n_med_verdi=' || count(*)::text,
       'median=' || percentile_disc(0.5) WITHIN GROUP (ORDER BY opened - to_date(aapnet_verdi,'DD.MM.YYYY'))::text || ' p90=' || percentile_disc(0.9) WITHIN GROUP (ORDER BY opened - to_date(aapnet_verdi,'DD.MM.YYYY'))::text,
       'innen7d=' || count(*) FILTER (WHERE (opened - to_date(aapnet_verdi,'DD.MM.YYYY')) BETWEEN 0 AND 7)::text, NULL
FROM c WHERE aapnet_verdi ~ '^[0-9]{2}[.][0-9]{2}[.][0-9]{4}$' GROUP BY 2
ORDER BY 1,2,3;
