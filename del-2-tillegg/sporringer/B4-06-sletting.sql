-- B4-06: deletion (Sletting) after innstilling vs after ordinary closure
WITH o AS (SELECT orgnr, min(dato) AS opened FROM kunngjoring.insolvens WHERE type='Konkurs - åpning' AND dato BETWEEN '2023-09-01' AND '2024-12-31' GROUP BY 1),
e AS (SELECT i.orgnr, min(i.dato) FILTER (WHERE i.type='Konkurs - innstilling av bobehandlingen') AS innstilt, min(i.dato) FILTER (WHERE i.type='Konkurs - avslutning av bobehandlingen') AS avsluttet FROM kunngjoring.insolvens i JOIN o USING (orgnr) WHERE i.dato >= o.opened AND i.dato <= DATE '2026-08-24' GROUP BY 1),
c AS (SELECT o.orgnr, o.opened, CASE WHEN e.innstilt IS NOT NULL THEN 'innstilt' WHEN e.avsluttet IS NOT NULL THEN 'avsluttet' ELSE 'aapen' END AS utfall, coalesce(e.innstilt,e.avsluttet) AS utfallsdato FROM o LEFT JOIN e USING (orgnr)),
d AS (SELECT c.*,
        (SELECT min(k.dato) FROM kunngjoring.kunngjoring k WHERE k.orgnr=c.orgnr AND k.type_kanon='Sletting' AND k.dato>=c.opened AND k.dato<=DATE '2026-08-24') AS slettet_kunngj,
        (SELECT s.slettet FROM kunngjoring.selskap s WHERE s.orgnr=c.orgnr) AS slettet_selskapstabell
      FROM c)
SELECT 'a_sletting_andel' AS hva, utfall, count(*) AS bo,
       count(slettet_kunngj) AS med_slettingskunngj,
       round(100.0*count(slettet_kunngj)/count(*),1) AS pct_slettet,
       count(slettet_selskapstabell) AS med_slettet_i_selskapstabell,
       count(*) FILTER (WHERE slettet_kunngj IS NOT NULL AND slettet_selskapstabell IS NOT NULL AND slettet_kunngj=slettet_selskapstabell) AS datoene_er_like
FROM d GROUP BY 2
UNION ALL SELECT 'a_sletting_andel','ALLE',count(*),count(slettet_kunngj),round(100.0*count(slettet_kunngj)/count(*),1),count(slettet_selskapstabell),
       count(*) FILTER (WHERE slettet_kunngj IS NOT NULL AND slettet_selskapstabell IS NOT NULL AND slettet_kunngj=slettet_selskapstabell) FROM d;

-- (b) days from outcome to deletion, by outcome
WITH o AS (SELECT orgnr, min(dato) AS opened FROM kunngjoring.insolvens WHERE type='Konkurs - åpning' AND dato BETWEEN '2023-09-01' AND '2024-12-31' GROUP BY 1),
e AS (SELECT i.orgnr, min(i.dato) FILTER (WHERE i.type='Konkurs - innstilling av bobehandlingen') AS innstilt, min(i.dato) FILTER (WHERE i.type='Konkurs - avslutning av bobehandlingen') AS avsluttet FROM kunngjoring.insolvens i JOIN o USING (orgnr) WHERE i.dato >= o.opened AND i.dato <= DATE '2026-08-24' GROUP BY 1),
c AS (SELECT o.orgnr, o.opened, CASE WHEN e.innstilt IS NOT NULL THEN 'innstilt' WHEN e.avsluttet IS NOT NULL THEN 'avsluttet' ELSE 'aapen' END AS utfall, coalesce(e.innstilt,e.avsluttet) AS utfallsdato FROM o LEFT JOIN e USING (orgnr)),
d AS (SELECT c.*, (SELECT min(k.dato) FROM kunngjoring.kunngjoring k WHERE k.orgnr=c.orgnr AND k.type_kanon='Sletting' AND k.dato>=c.opened AND k.dato<=DATE '2026-08-24') AS slettet FROM c)
SELECT 'b_dager_utfall_til_sletting' AS hva, utfall, count(*) FILTER (WHERE slettet IS NOT NULL) AS n,
       min(slettet-utfallsdato) AS min_d,
       percentile_cont(0.10) WITHIN GROUP (ORDER BY (slettet-utfallsdato)) AS p10,
       percentile_cont(0.25) WITHIN GROUP (ORDER BY (slettet-utfallsdato)) AS q1,
       percentile_cont(0.50) WITHIN GROUP (ORDER BY (slettet-utfallsdato)) AS median,
       percentile_cont(0.75) WITHIN GROUP (ORDER BY (slettet-utfallsdato)) AS q3,
       percentile_cont(0.90) WITHIN GROUP (ORDER BY (slettet-utfallsdato)) AS p90,
       max(slettet-utfallsdato) AS max_d,
       count(*) FILTER (WHERE slettet IS NOT NULL AND slettet < utfallsdato) AS slettet_for_utfall,
       count(*) FILTER (WHERE slettet = utfallsdato) AS samme_dag,
       count(*) FILTER (WHERE slettet IS NOT NULL AND slettet-utfallsdato BETWEEN 1 AND 30) AS innen_30d,
       count(*) FILTER (WHERE slettet IS NOT NULL AND slettet-utfallsdato BETWEEN 1 AND 90) AS innen_90d
FROM d WHERE utfall<>'aapen' GROUP BY 2;

-- (c) days from OPENING to deletion, by outcome
WITH o AS (SELECT orgnr, min(dato) AS opened FROM kunngjoring.insolvens WHERE type='Konkurs - åpning' AND dato BETWEEN '2023-09-01' AND '2024-12-31' GROUP BY 1),
e AS (SELECT i.orgnr, min(i.dato) FILTER (WHERE i.type='Konkurs - innstilling av bobehandlingen') AS innstilt, min(i.dato) FILTER (WHERE i.type='Konkurs - avslutning av bobehandlingen') AS avsluttet FROM kunngjoring.insolvens i JOIN o USING (orgnr) WHERE i.dato >= o.opened AND i.dato <= DATE '2026-08-24' GROUP BY 1),
c AS (SELECT o.orgnr, o.opened, CASE WHEN e.innstilt IS NOT NULL THEN 'innstilt' WHEN e.avsluttet IS NOT NULL THEN 'avsluttet' ELSE 'aapen' END AS utfall, coalesce(e.innstilt,e.avsluttet) AS utfallsdato FROM o LEFT JOIN e USING (orgnr)),
d AS (SELECT c.*, (SELECT min(k.dato) FROM kunngjoring.kunngjoring k WHERE k.orgnr=c.orgnr AND k.type_kanon='Sletting' AND k.dato>=c.opened AND k.dato<=DATE '2026-08-24') AS slettet FROM c)
SELECT 'c_dager_apning_til_sletting' AS hva, utfall, count(*) FILTER (WHERE slettet IS NOT NULL) AS n,
       percentile_cont(0.25) WITHIN GROUP (ORDER BY (slettet-opened)) AS q1,
       percentile_cont(0.50) WITHIN GROUP (ORDER BY (slettet-opened)) AS median,
       percentile_cont(0.75) WITHIN GROUP (ORDER BY (slettet-opened)) AS q3
FROM d GROUP BY 2;

-- (d) fixed-horizon check: outcome on or before 2026-02-24, i.e. at least 180 days of deletion follow-up
WITH o AS (SELECT orgnr, min(dato) AS opened FROM kunngjoring.insolvens WHERE type='Konkurs - åpning' AND dato BETWEEN '2023-09-01' AND '2024-12-31' GROUP BY 1),
e AS (SELECT i.orgnr, min(i.dato) FILTER (WHERE i.type='Konkurs - innstilling av bobehandlingen') AS innstilt, min(i.dato) FILTER (WHERE i.type='Konkurs - avslutning av bobehandlingen') AS avsluttet FROM kunngjoring.insolvens i JOIN o USING (orgnr) WHERE i.dato >= o.opened AND i.dato <= DATE '2026-08-24' GROUP BY 1),
c AS (SELECT o.orgnr, o.opened, CASE WHEN e.innstilt IS NOT NULL THEN 'innstilt' WHEN e.avsluttet IS NOT NULL THEN 'avsluttet' ELSE 'aapen' END AS utfall, coalesce(e.innstilt,e.avsluttet) AS utfallsdato FROM o LEFT JOIN e USING (orgnr)),
d AS (SELECT c.*, (SELECT min(k.dato) FROM kunngjoring.kunngjoring k WHERE k.orgnr=c.orgnr AND k.type_kanon='Sletting' AND k.dato>=c.opened AND k.dato<=DATE '2026-08-24') AS slettet FROM c)
SELECT 'd_fast_horisont_180d' AS hva, utfall, count(*) AS bo_med_utfall_senest_20260224,
       count(*) FILTER (WHERE slettet IS NOT NULL AND slettet <= utfallsdato + 180) AS slettet_innen_180d,
       round(100.0*count(*) FILTER (WHERE slettet IS NOT NULL AND slettet <= utfallsdato + 180)/count(*),1) AS pct
FROM d WHERE utfall<>'aapen' AND utfallsdato <= DATE '2026-02-24' GROUP BY 2;

-- (e) which register publishes the Sletting, and how many distinct Sletting dates per estate
WITH o AS (SELECT orgnr, min(dato) AS opened FROM kunngjoring.insolvens WHERE type='Konkurs - åpning' AND dato BETWEEN '2023-09-01' AND '2024-12-31' GROUP BY 1)
SELECT 'e_sletting_register' AS hva, coalesce(k.register,'<NULL>') AS register, count(*) AS rader, count(DISTINCT k.orgnr) AS selskaper
FROM o JOIN kunngjoring.kunngjoring k ON k.orgnr=o.orgnr AND k.type_kanon='Sletting' AND k.dato>=o.opened GROUP BY 2 ORDER BY 4 DESC;
