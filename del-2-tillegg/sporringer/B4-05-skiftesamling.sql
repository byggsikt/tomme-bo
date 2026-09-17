-- B4-05: skiftesamling / fordringsfrist / fordringshavermøte announcements per estate, cohort + corpus timeline
WITH o AS (SELECT orgnr, min(dato) AS opened FROM kunngjoring.insolvens WHERE type='Konkurs - åpning' AND dato BETWEEN '2023-09-01' AND '2024-12-31' GROUP BY 1),
e AS (SELECT i.orgnr, min(i.dato) FILTER (WHERE i.type='Konkurs - innstilling av bobehandlingen') AS innstilt, min(i.dato) FILTER (WHERE i.type='Konkurs - avslutning av bobehandlingen') AS avsluttet FROM kunngjoring.insolvens i JOIN o USING (orgnr) WHERE i.dato >= o.opened AND i.dato <= DATE '2026-08-24' GROUP BY 1),
c AS (SELECT o.orgnr, o.opened, CASE WHEN e.innstilt IS NOT NULL THEN 'innstilt' WHEN e.avsluttet IS NOT NULL THEN 'avsluttet' ELSE 'aapen' END AS utfall, e.innstilt, e.avsluttet, coalesce(e.innstilt, e.avsluttet) AS utfallsdato FROM o LEFT JOIN e USING (orgnr)),
s AS (SELECT c.orgnr, c.utfall, c.opened, c.utfallsdato,
        count(DISTINCT k.dato) FILTER (WHERE k.type ~* 'skiftesamling')      AS n_skiftesamling_datoer,
        count(DISTINCT k.dato) FILTER (WHERE k.type ~* 'fordringsfrist')     AS n_fordringsfrist_datoer,
        count(DISTINCT k.dato) FILTER (WHERE k.type ~* 'fordringshavermøte') AS n_fordringshavermote_datoer,
        count(DISTINCT k.dato) FILTER (WHERE k.type ~* 'ny bostyrer')        AS n_ny_bostyrer_datoer,
        min(k.dato) FILTER (WHERE k.type ~* 'skiftesamling') AS forste_skiftesamling_kunngj
      FROM c LEFT JOIN kunngjoring.kunngjoring k ON k.orgnr=c.orgnr AND k.dato >= c.opened AND k.dato <= DATE '2026-08-24'
      GROUP BY 1,2,3,4)
SELECT 'a_per_bo' AS hva, utfall,
       count(*) AS bo,
       count(*) FILTER (WHERE n_skiftesamling_datoer > 0) AS med_skiftesamling_kunngj,
       count(*) FILTER (WHERE n_skiftesamling_datoer > 1) AS med_flere_skiftesamling,
       count(*) FILTER (WHERE n_fordringsfrist_datoer > 0) AS med_ny_fordringsfrist,
       count(*) FILTER (WHERE n_fordringshavermote_datoer > 0) AS med_fordringshavermote,
       count(*) FILTER (WHERE n_ny_bostyrer_datoer > 0) AS med_ny_bostyrer
FROM s GROUP BY 2
UNION ALL
SELECT 'a_per_bo','ALLE', count(*), count(*) FILTER (WHERE n_skiftesamling_datoer>0), count(*) FILTER (WHERE n_skiftesamling_datoer>1),
       count(*) FILTER (WHERE n_fordringsfrist_datoer>0), count(*) FILTER (WHERE n_fordringshavermote_datoer>0), count(*) FILTER (WHERE n_ny_bostyrer_datoer>0)
FROM s;

-- (b) outcome of the estates that DID have a skiftesamling / ny bostyrer announcement
WITH o AS (SELECT orgnr, min(dato) AS opened FROM kunngjoring.insolvens WHERE type='Konkurs - åpning' AND dato BETWEEN '2023-09-01' AND '2024-12-31' GROUP BY 1),
e AS (SELECT i.orgnr, min(i.dato) FILTER (WHERE i.type='Konkurs - innstilling av bobehandlingen') AS innstilt, min(i.dato) FILTER (WHERE i.type='Konkurs - avslutning av bobehandlingen') AS avsluttet FROM kunngjoring.insolvens i JOIN o USING (orgnr) WHERE i.dato >= o.opened AND i.dato <= DATE '2026-08-24' GROUP BY 1),
c AS (SELECT o.orgnr, o.opened, CASE WHEN e.innstilt IS NOT NULL THEN 'innstilt' WHEN e.avsluttet IS NOT NULL THEN 'avsluttet' ELSE 'aapen' END AS utfall, coalesce(e.innstilt,e.avsluttet) AS utfallsdato FROM o LEFT JOIN e USING (orgnr)),
s AS (SELECT c.orgnr, c.utfall, c.opened, c.utfallsdato,
        count(DISTINCT k.dato) FILTER (WHERE k.type ~* 'skiftesamling') AS n_sk,
        count(DISTINCT k.dato) FILTER (WHERE k.type ~* 'ny bostyrer')   AS n_nb
      FROM c LEFT JOIN kunngjoring.kunngjoring k ON k.orgnr=c.orgnr AND k.dato >= c.opened AND k.dato <= DATE '2026-08-24' GROUP BY 1,2,3,4)
SELECT 'b_utfall_gitt_signal' AS hva, sig, count(*) AS bo,
       count(*) FILTER (WHERE utfall='innstilt') AS innstilt,
       count(*) FILTER (WHERE utfall='avsluttet') AS avsluttet,
       count(*) FILTER (WHERE utfall='aapen') AS aapen,
       round(100.0*count(*) FILTER (WHERE utfall='innstilt')/nullif(count(*) FILTER (WHERE utfall<>'aapen'),0),1) AS pct_innstilt_av_avgjorte,
       percentile_cont(0.5) WITHIN GROUP (ORDER BY (utfallsdato-opened)) AS median_dager_til_utfall
FROM (SELECT *, CASE WHEN n_sk>0 AND n_nb>0 THEN '3_begge' WHEN n_sk>0 THEN '1_skiftesamling' WHEN n_nb>0 THEN '2_ny_bostyrer' ELSE '0_ingen' END AS sig FROM s) z
GROUP BY 2 ORDER BY 2;

-- (c) the corpus timeline of skiftesamling/fordringsfrist announcements per calendar year (is this a practice that exists at all?)
SELECT 'c_korpus_aarsserie' AS hva, extract(year FROM k.dato)::int AS aar,
       count(DISTINCT k.orgnr) FILTER (WHERE k.type ~* 'skiftesamling') AS selskaper_skiftesamling,
       count(DISTINCT k.orgnr) FILTER (WHERE k.type ~* 'fordringsfrist') AS selskaper_fordringsfrist,
       count(DISTINCT k.orgnr) FILTER (WHERE k.type='Konkurs - åpning') AS selskaper_apning
FROM kunngjoring.kunngjoring k
WHERE k.dato >= '2016-01-01' AND (k.type ~* '(skiftesamling|fordringsfrist)' OR k.type='Konkurs - åpning')
GROUP BY 2 ORDER BY 2;

-- (d) cohort estates listed with >1 skiftesamling date, for reading
WITH o AS (SELECT orgnr, min(dato) AS opened FROM kunngjoring.insolvens WHERE type='Konkurs - åpning' AND dato BETWEEN '2023-09-01' AND '2024-12-31' GROUP BY 1),
e AS (SELECT i.orgnr, min(i.dato) FILTER (WHERE i.type='Konkurs - innstilling av bobehandlingen') AS innstilt, min(i.dato) FILTER (WHERE i.type='Konkurs - avslutning av bobehandlingen') AS avsluttet FROM kunngjoring.insolvens i JOIN o USING (orgnr) WHERE i.dato >= o.opened AND i.dato <= DATE '2026-08-24' GROUP BY 1),
c AS (SELECT o.orgnr, o.opened, CASE WHEN e.innstilt IS NOT NULL THEN 'innstilt' WHEN e.avsluttet IS NOT NULL THEN 'avsluttet' ELSE 'aapen' END AS utfall, coalesce(e.innstilt,e.avsluttet) AS utfallsdato FROM o LEFT JOIN e USING (orgnr))
SELECT 'd_skiftesamling_rader' AS hva, c.orgnr, c.utfall, c.opened, c.utfallsdato, k.dato, left(k.type,70) AS type
FROM c JOIN kunngjoring.kunngjoring k ON k.orgnr=c.orgnr AND k.dato >= c.opened AND k.type ~* '(skiftesamling|fordringsfrist|fordringshavermøte)'
GROUP BY 2,3,4,5,6,7 ORDER BY 2,6;
