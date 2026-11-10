-- V-B3: independent re-check of (a) amount_unit semantics and (b) the filing-time of the accounts used.
WITH o AS (SELECT orgnr, min(dato) AS opened FROM kunngjoring.insolvens
           WHERE type='Konkurs - åpning' AND dato BETWEEN '2023-09-01' AND '2024-12-31' GROUP BY 1),
a AS (SELECT a.*, o.opened FROM company_intel.annual_account a JOIN o ON a.orgnr=trim(o.orgnr)
      WHERE a.fiscal_year < extract(year FROM o.opened))
SELECT 'enhet' AS hva, coalesce(nullif(a.amount_unit,''),'<BLANK>') AS unit, a.source_name,
       count(*) AS rader,
       count(*) FILTER (WHERE a.total_assets IS NOT NULL AND (a.total_assets::numeric % 1000) <> 0) AS ikke_multiplum_1000,
       round(percentile_cont(0.5) WITHIN GROUP (ORDER BY a.total_assets)) AS median_ta
FROM a GROUP BY 2,3 ORDER BY 2,3;
-- overlapping (orgnr, fiscal_year) pairs present in BOTH sources: are the values identical or a factor 1000 apart?
WITH o AS (SELECT orgnr, min(dato) AS opened FROM kunngjoring.insolvens
           WHERE type='Konkurs - åpning' AND dato BETWEEN '2023-09-01' AND '2024-12-31' GROUP BY 1),
a AS (SELECT a.* FROM company_intel.annual_account a JOIN o ON a.orgnr=trim(o.orgnr)
      WHERE a.fiscal_year < extract(year FROM o.opened))
SELECT 'par' AS hva, count(*) AS par,
       count(*) FILTER (WHERE r.total_assets IS NOT DISTINCT FROM g.total_assets) AS lik_ta,
       count(*) FILTER (WHERE r.equity IS NOT DISTINCT FROM g.equity) AS lik_ek,
       count(*) FILTER (WHERE r.liabilities IS NOT DISTINCT FROM g.liabilities) AS lik_gjeld,
       count(*) FILTER (WHERE r.current_assets IS NOT DISTINCT FROM g.current_assets) AS lik_om,
       count(*) FILTER (WHERE r.operating_revenue IS NOT DISTINCT FROM g.operating_revenue) AS lik_rev,
       count(*) FILTER (WHERE g.total_assets<>0 AND abs(r.total_assets*1000-g.total_assets)<1) AS faktor1000
FROM a r JOIN a g ON g.orgnr=r.orgnr AND g.fiscal_year=r.fiscal_year
     AND r.source_name='brreg-recovered' AND g.source_name='brreg-regnskap';
-- timing: which opening months use which fiscal year (an FY(t-1) account for an opening early in year t
-- was filed AFTER the opening in ordinary practice)
WITH o AS (SELECT orgnr, min(dato) AS opened FROM kunngjoring.insolvens
           WHERE type='Konkurs - åpning' AND dato BETWEEN '2023-09-01' AND '2024-12-31' GROUP BY 1),
acc AS (SELECT DISTINCT ON (a.orgnr) a.orgnr, a.fiscal_year, o.opened
        FROM company_intel.annual_account a JOIN o ON a.orgnr=trim(o.orgnr)
        WHERE a.fiscal_year < extract(year FROM o.opened)
        ORDER BY a.orgnr, a.fiscal_year DESC, (a.source_name='brreg-regnskap') DESC)
SELECT 'timing' AS hva, extract(year FROM opened)::int AS aar_apnet,
       CASE WHEN extract(month FROM opened) <= 7 THEN 'jan-jul' ELSE 'aug-des' END AS halvaar,
       count(*) AS bo,
       count(*) FILTER (WHERE fiscal_year = extract(year FROM opened)-1) AS bruker_fjoraaret,
       round(100.0*count(*) FILTER (WHERE fiscal_year = extract(year FROM opened)-1)/count(*),1) AS pst
FROM acc GROUP BY 2,3 ORDER BY 2,3;
