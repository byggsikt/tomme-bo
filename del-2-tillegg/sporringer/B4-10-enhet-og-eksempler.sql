-- B4-10: (a) unit sanity for operating_revenue/total_assets across the two sources, measured on the companies present in BOTH
WITH o AS (SELECT orgnr, min(dato) AS opened FROM kunngjoring.insolvens WHERE type='Konkurs - åpning' AND dato BETWEEN '2023-09-01' AND '2024-12-31' GROUP BY 1),
r AS (SELECT a.orgnr, a.fiscal_year, a.source_name, a.amount_unit, a.total_assets, a.operating_revenue
      FROM o JOIN company_intel.annual_account a ON a.orgnr=o.orgnr::text),
p AS (SELECT x.orgnr, x.fiscal_year, x.total_assets AS ta_rec, y.total_assets AS ta_reg, x.operating_revenue AS or_rec, y.operating_revenue AS or_reg
      FROM r x JOIN r y ON x.orgnr=y.orgnr AND x.fiscal_year=y.fiscal_year AND x.source_name='brreg-recovered' AND y.source_name='brreg-regnskap')
SELECT 'a_enhetssjekk' AS hva, count(*) AS par,
       count(*) FILTER (WHERE ta_rec = ta_reg) AS ta_identisk,
       count(*) FILTER (WHERE ta_rec IS NOT NULL AND ta_reg IS NOT NULL AND ta_rec <> ta_reg) AS ta_ulike,
       count(*) FILTER (WHERE abs(ta_rec - ta_reg*1000) < 1) AS ta_faktor_1000,
       count(*) FILTER (WHERE or_rec = or_reg) AS oms_identisk,
       count(*) FILTER (WHERE or_rec IS NOT NULL AND or_reg IS NOT NULL AND or_rec <> or_reg) AS oms_ulike
FROM p;

-- (b) magnitude sanity: percentiles of operating_revenue per source (whole kroner would put the median in the low millions)
WITH o AS (SELECT orgnr, min(dato) AS opened FROM kunngjoring.insolvens WHERE type='Konkurs - åpning' AND dato BETWEEN '2023-09-01' AND '2024-12-31' GROUP BY 1)
SELECT 'b_magnitude' AS hva, a.source_name, coalesce(a.amount_unit,'<NULL>') AS unit, count(a.operating_revenue) AS n,
       percentile_cont(0.10) WITHIN GROUP (ORDER BY a.operating_revenue) AS p10,
       percentile_cont(0.50) WITHIN GROUP (ORDER BY a.operating_revenue) AS median,
       percentile_cont(0.90) WITHIN GROUP (ORDER BY a.operating_revenue) AS p90,
       max(a.operating_revenue) AS maks
FROM o JOIN company_intel.annual_account a ON a.orgnr=o.orgnr::text WHERE a.operating_revenue IS NOT NULL GROUP BY 2,3;

-- (c) examples to fetch from the live source: the three largest innstilte estates by last-known revenue
WITH o AS (SELECT orgnr, min(dato) AS opened FROM kunngjoring.insolvens WHERE type='Konkurs - åpning' AND dato BETWEEN '2023-09-01' AND '2024-12-31' GROUP BY 1),
e AS (SELECT i.orgnr, min(i.dato) FILTER (WHERE i.type='Konkurs - innstilling av bobehandlingen') AS innstilt, min(i.dato) FILTER (WHERE i.type='Konkurs - avslutning av bobehandlingen') AS avsluttet FROM kunngjoring.insolvens i JOIN o USING (orgnr) WHERE i.dato >= o.opened AND i.dato <= DATE '2026-08-24' GROUP BY 1),
c AS (SELECT o.orgnr, o.opened, CASE WHEN e.innstilt IS NOT NULL THEN 'innstilt' WHEN e.avsluttet IS NOT NULL THEN 'avsluttet' ELSE 'aapen' END AS utfall, e.innstilt FROM o LEFT JOIN e USING (orgnr)),
last AS (SELECT DISTINCT ON (a.orgnr) a.orgnr, a.fiscal_year, a.operating_revenue, a.total_assets
         FROM company_intel.annual_account a JOIN c ON a.orgnr=c.orgnr::text
         WHERE a.fiscal_year <= extract(year FROM c.opened)::int
         ORDER BY a.orgnr, a.fiscal_year DESC, (a.source_name='brreg-regnskap') DESC)
SELECT 'c_storste_innstilte' AS hva, c.orgnr, s.navn_gjeldende, c.opened, c.innstilt, (c.innstilt-c.opened) AS dager, l.fiscal_year, l.operating_revenue, l.total_assets
FROM c JOIN last l ON l.orgnr=c.orgnr::text LEFT JOIN kunngjoring.selskap s ON s.orgnr=c.orgnr
WHERE c.utfall='innstilt' ORDER BY l.operating_revenue DESC NULLS LAST LIMIT 10;

-- (d) time from opening to innstilling / to avslutning, so the adviser number is in the report
WITH o AS (SELECT orgnr, min(dato) AS opened FROM kunngjoring.insolvens WHERE type='Konkurs - åpning' AND dato BETWEEN '2023-09-01' AND '2024-12-31' GROUP BY 1),
e AS (SELECT i.orgnr, min(i.dato) FILTER (WHERE i.type='Konkurs - innstilling av bobehandlingen') AS innstilt, min(i.dato) FILTER (WHERE i.type='Konkurs - avslutning av bobehandlingen') AS avsluttet FROM kunngjoring.insolvens i JOIN o USING (orgnr) WHERE i.dato >= o.opened AND i.dato <= DATE '2026-08-24' GROUP BY 1),
c AS (SELECT o.orgnr, o.opened, CASE WHEN e.innstilt IS NOT NULL THEN 'innstilt' WHEN e.avsluttet IS NOT NULL THEN 'avsluttet' ELSE 'aapen' END AS utfall, coalesce(e.innstilt,e.avsluttet) AS utfallsdato FROM o LEFT JOIN e USING (orgnr))
SELECT 'd_tid_til_utfall' AS hva, utfall, count(*) AS n,
       percentile_cont(0.10) WITHIN GROUP (ORDER BY (utfallsdato-opened)) AS p10,
       percentile_cont(0.25) WITHIN GROUP (ORDER BY (utfallsdato-opened)) AS q1,
       percentile_cont(0.50) WITHIN GROUP (ORDER BY (utfallsdato-opened)) AS median,
       percentile_cont(0.75) WITHIN GROUP (ORDER BY (utfallsdato-opened)) AS q3,
       percentile_cont(0.90) WITHIN GROUP (ORDER BY (utfallsdato-opened)) AS p90
FROM c WHERE utfall<>'aapen' GROUP BY 2;

-- (e) revenue band x outcome, restricted to the assumption-free 730-day sub-cohort (opened on or before 2024-08-24)
WITH o AS (SELECT orgnr, min(dato) AS opened FROM kunngjoring.insolvens WHERE type='Konkurs - åpning' AND dato BETWEEN '2023-09-01' AND '2024-12-31' GROUP BY 1),
e AS (SELECT i.orgnr, min(i.dato) FILTER (WHERE i.type='Konkurs - innstilling av bobehandlingen') AS innstilt, min(i.dato) FILTER (WHERE i.type='Konkurs - avslutning av bobehandlingen') AS avsluttet FROM kunngjoring.insolvens i JOIN o USING (orgnr) WHERE i.dato >= o.opened AND i.dato <= DATE '2026-08-24' GROUP BY 1),
c AS (SELECT o.orgnr, o.opened,
        CASE WHEN e.innstilt IS NOT NULL AND e.innstilt <= o.opened+730 THEN 'innstilt'
             WHEN e.avsluttet IS NOT NULL AND e.avsluttet <= o.opened+730 AND (e.innstilt IS NULL OR e.innstilt > o.opened+730) THEN 'avsluttet'
             ELSE 'aapen_ved_730d' END AS utfall730
      FROM o LEFT JOIN e USING (orgnr) WHERE o.opened <= DATE '2024-08-24'),
last AS (SELECT DISTINCT ON (a.orgnr) a.orgnr, a.operating_revenue
         FROM company_intel.annual_account a JOIN c ON a.orgnr=c.orgnr::text
         WHERE a.fiscal_year <= extract(year FROM c.opened)::int
         ORDER BY a.orgnr, a.fiscal_year DESC, (a.source_name='brreg-regnskap') DESC)
SELECT 'e_730d_band' AS hva,
       CASE WHEN l.orgnr IS NULL THEN '5_ingen_regnskap'
            WHEN l.operating_revenue IS NULL THEN '4_ingen_omsetning'
            WHEN l.operating_revenue < 1000000 THEN '0_under_1m'
            WHEN l.operating_revenue < 5000000 THEN '1_1_5m'
            WHEN l.operating_revenue < 20000000 THEN '2_5_20m'
            ELSE '3_over_20m' END AS band,
       count(*) AS bo,
       count(*) FILTER (WHERE utfall730='innstilt') AS innstilt,
       count(*) FILTER (WHERE utfall730='avsluttet') AS avsluttet,
       count(*) FILTER (WHERE utfall730='aapen_ved_730d') AS fortsatt_aapen
FROM c LEFT JOIN last l ON l.orgnr=c.orgnr::text GROUP BY 2 ORDER BY 2;
