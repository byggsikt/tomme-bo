-- B3: amount_unit normalisation evidence for the cohort's pre-opening accounts. READ-ONLY.
WITH o AS (SELECT orgnr, min(dato) AS opened FROM kunngjoring.insolvens WHERE type='Konkurs - åpning' AND dato BETWEEN '2023-09-01' AND '2024-12-31' GROUP BY 1),
a AS (SELECT a.* FROM company_intel.annual_account a JOIN o ON a.orgnr=o.orgnr::text WHERE a.fiscal_year < extract(year FROM o.opened))
SELECT 'unit_inventory' AS hva, coalesce(a.amount_unit,'<NULL>') AS unit, a.source_name, coalesce(a.currency,'<NULL>') AS cur, count(*) AS rader, count(DISTINCT a.orgnr) AS selskaper,
       count(*) FILTER (WHERE a.total_assets IS NOT NULL AND a.total_assets % 1000 <> 0) AS ta_not_mult_1000,
       count(*) FILTER (WHERE a.total_assets = 0) AS ta_zero,
       count(*) FILTER (WHERE a.total_assets IS NOT NULL AND a.total_assets > 0 AND a.total_assets < 1000) AS ta_under_1000,
       percentile_cont(0.5) WITHIN GROUP (ORDER BY a.total_assets) AS med_ta,
       percentile_cont(0.5) WITHIN GROUP (ORDER BY a.operating_revenue) AS med_rev,
       count(a.current_assets) AS has_ca, count(a.equity) AS has_eq, count(a.operating_revenue) AS has_rev, count(a.payroll_expenses) AS has_payroll
FROM a GROUP BY 2,3,4 ORDER BY 2,3,4;
WITH o AS (SELECT orgnr, min(dato) AS opened FROM kunngjoring.insolvens WHERE type='Konkurs - åpning' AND dato BETWEEN '2023-09-01' AND '2024-12-31' GROUP BY 1),
a AS (SELECT a.* FROM company_intel.annual_account a JOIN o ON a.orgnr=o.orgnr::text WHERE a.fiscal_year < extract(year FROM o.opened))
SELECT 'pair_compare' AS hva, count(*) AS par,
       count(*) FILTER (WHERE r.total_assets = g.total_assets) AS eq_ta,
       count(*) FILTER (WHERE r.current_assets = g.current_assets) AS eq_ca,
       count(*) FILTER (WHERE r.equity = g.equity) AS eq_eq,
       count(*) FILTER (WHERE r.operating_revenue = g.operating_revenue) AS eq_rev,
       count(*) FILTER (WHERE r.liabilities = g.liabilities) AS eq_liab,
       count(*) FILTER (WHERE r.operating_revenue IS NULL OR g.operating_revenue IS NULL) AS rev_null_either,
       count(*) FILTER (WHERE abs(r.total_assets*1000 - g.total_assets) < 1000 AND g.total_assets <> 0) AS r_x1000_eq_g,
       count(*) FILTER (WHERE abs(g.total_assets*1000 - r.total_assets) < 1000 AND r.total_assets <> 0) AS g_x1000_eq_r
FROM a r JOIN a g ON g.orgnr=r.orgnr AND g.fiscal_year=r.fiscal_year AND r.source_name='brreg-recovered' AND g.source_name='brreg-regnskap';
WITH o AS (SELECT orgnr, min(dato) AS opened FROM kunngjoring.insolvens WHERE type='Konkurs - åpning' AND dato BETWEEN '2023-09-01' AND '2024-12-31' GROUP BY 1),
a AS (SELECT a.*, o.opened FROM company_intel.annual_account a JOIN o ON a.orgnr=o.orgnr::text)
SELECT 'acc_only_at_or_after_opening_year' AS hva, a.fiscal_year, extract(year FROM a.opened)::int AS aar_apnet, a.source_name, count(*) AS n, percentile_cont(0.5) WITHIN GROUP (ORDER BY a.total_assets) AS med_ta
FROM a WHERE NOT EXISTS (SELECT 1 FROM company_intel.annual_account b WHERE b.orgnr=a.orgnr AND b.fiscal_year < extract(year FROM a.opened))
GROUP BY 2,3,4 ORDER BY 2,3,4;
