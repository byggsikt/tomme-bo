WITH o AS (SELECT orgnr, min(dato) AS opened FROM kunngjoring.insolvens WHERE type='Konkurs - åpning' AND dato BETWEEN '2023-09-01' AND '2024-12-31' GROUP BY 1)
, a AS (SELECT a.* FROM company_intel.annual_account a JOIN o ON a.orgnr=o.orgnr::text)
SELECT '--- A1: non-NOK rows (orgnr, fy, cur, source) ---' AS x;
WITH o AS (SELECT orgnr, min(dato) AS opened FROM kunngjoring.insolvens WHERE type='Konkurs - åpning' AND dato BETWEEN '2023-09-01' AND '2024-12-31' GROUP BY 1)
SELECT a.orgnr, a.fiscal_year, a.currency, a.source_name, a.total_assets, a.equity, a.operating_revenue
FROM company_intel.annual_account a JOIN o ON a.orgnr=o.orgnr::text WHERE coalesce(a.currency,'NOK')<>'NOK' ORDER BY 1,2;

SELECT '--- A2: overlapping (orgnr,fy) pairs across the two sources ---' AS x;
WITH o AS (SELECT orgnr, min(dato) AS opened FROM kunngjoring.insolvens WHERE type='Konkurs - åpning' AND dato BETWEEN '2023-09-01' AND '2024-12-31' GROUP BY 1),
a AS (SELECT a.* FROM company_intel.annual_account a JOIN o ON a.orgnr=o.orgnr::text),
p AS (SELECT r.orgnr, r.fiscal_year, r.total_assets AS ta_reg, r.equity AS eq_reg, r.operating_revenue AS rev_reg,
             b.total_assets AS ta_rec, b.equity AS eq_rec, b.operating_revenue AS rev_rec
      FROM a r JOIN a b ON r.orgnr=b.orgnr AND r.fiscal_year=b.fiscal_year
      WHERE r.source_name='brreg-regnskap' AND b.source_name='brreg-recovered')
SELECT count(*) AS n_pairs,
       count(*) FILTER (WHERE ta_reg IS NOT DISTINCT FROM ta_rec) AS ta_equal,
       count(*) FILTER (WHERE eq_reg IS NOT DISTINCT FROM eq_rec) AS eq_equal,
       count(*) FILTER (WHERE rev_reg IS NOT DISTINCT FROM rev_rec) AS rev_equal,
       count(*) FILTER (WHERE ta_reg IS NOT NULL AND ta_rec IS NOT NULL AND ta_rec<>0 AND abs(ta_reg/nullif(ta_rec,0)-1000)<1) AS ta_ratio_1000,
       count(*) FILTER (WHERE ta_reg IS NOT NULL AND ta_rec IS NOT NULL AND ta_reg<>0 AND abs(ta_rec/nullif(ta_reg,0)-1000)<1) AS ta_ratio_inv1000
FROM p;

SELECT '--- A3: multiples of 1000 test, by source ---' AS x;
WITH o AS (SELECT orgnr, min(dato) AS opened FROM kunngjoring.insolvens WHERE type='Konkurs - åpning' AND dato BETWEEN '2023-09-01' AND '2024-12-31' GROUP BY 1)
SELECT a.source_name, coalesce(a.amount_unit,'<NULL>') AS unit,
  count(*) FILTER (WHERE a.total_assets IS NOT NULL AND a.total_assets<>0) AS n_ta,
  count(*) FILTER (WHERE a.total_assets IS NOT NULL AND a.total_assets<>0 AND (a.total_assets::bigint % 1000)=0) AS ta_mult1000,
  count(*) FILTER (WHERE a.operating_revenue IS NOT NULL AND a.operating_revenue<>0) AS n_rev,
  count(*) FILTER (WHERE a.operating_revenue IS NOT NULL AND a.operating_revenue<>0 AND (a.operating_revenue::bigint % 1000)=0) AS rev_mult1000
FROM company_intel.annual_account a JOIN o ON a.orgnr=o.orgnr::text
WHERE coalesce(a.currency,'NOK')='NOK' GROUP BY 1,2 ORDER BY 1,2;

SELECT '--- A4: equity exactly at classic AS share-capital levels (NOK) ---' AS x;
WITH o AS (SELECT orgnr, min(dato) AS opened FROM kunngjoring.insolvens WHERE type='Konkurs - åpning' AND dato BETWEEN '2023-09-01' AND '2024-12-31' GROUP BY 1)
SELECT v, count(*) FROM (
  SELECT CASE WHEN a.equity IN (30000,100000,1000000) THEN 'NOK-level '||a.equity::bigint
              WHEN a.equity IN (30,100,1000) THEN 'TNOK-level '||a.equity::bigint ELSE 'other' END AS v
  FROM company_intel.annual_account a JOIN o ON a.orgnr=o.orgnr::text WHERE coalesce(a.currency,'NOK')='NOK') s
GROUP BY 1 ORDER BY 2 DESC;

SELECT '--- A5: total_assets vs registered share capital (kunngjoring.kapital, NOK) ---' AS x;
WITH o AS (SELECT orgnr, min(dato) AS opened FROM kunngjoring.insolvens WHERE type='Konkurs - åpning' AND dato BETWEEN '2023-09-01' AND '2024-12-31' GROUP BY 1),
k AS (SELECT DISTINCT ON (orgnr) orgnr, belop FROM kunngjoring.kapital WHERE belop IS NOT NULL AND orgnr IN (SELECT orgnr FROM o) ORDER BY orgnr, dato DESC),
a AS (SELECT DISTINCT ON (a.orgnr) a.orgnr, a.total_assets, a.equity, a.source_name FROM company_intel.annual_account a JOIN o ON a.orgnr=o.orgnr::text WHERE coalesce(a.currency,'NOK')='NOK' ORDER BY a.orgnr, a.fiscal_year DESC)
SELECT count(*) AS n,
  round(100.0*count(*) FILTER (WHERE a.total_assets >= k.belop)/count(*),1) AS pct_ta_ge_kapital,
  round(100.0*count(*) FILTER (WHERE a.total_assets*1000 >= k.belop)/count(*),1) AS pct_ta1000_ge_kapital,
  percentile_cont(0.5) WITHIN GROUP (ORDER BY a.total_assets) AS med_ta,
  percentile_cont(0.5) WITHIN GROUP (ORDER BY k.belop) AS med_kapital,
  percentile_cont(0.5) WITHIN GROUP (ORDER BY a.total_assets/nullif(k.belop,0)) AS med_ratio
FROM a JOIN k ON a.orgnr=k.orgnr::text WHERE a.total_assets IS NOT NULL AND k.belop>0;

SELECT '--- A6: distribution of total_assets (last pre-open row) ---' AS x;
WITH o AS (SELECT orgnr, min(dato) AS opened FROM kunngjoring.insolvens WHERE type='Konkurs - åpning' AND dato BETWEEN '2023-09-01' AND '2024-12-31' GROUP BY 1),
a AS (SELECT DISTINCT ON (a.orgnr) a.orgnr, a.total_assets, a.operating_revenue FROM company_intel.annual_account a JOIN o ON a.orgnr=o.orgnr::text WHERE coalesce(a.currency,'NOK')='NOK' AND a.fiscal_year < extract(year FROM o.opened) ORDER BY a.orgnr, a.fiscal_year DESC)
SELECT count(*) AS n,
 percentile_cont(0.05) WITHIN GROUP (ORDER BY total_assets) AS p05,
 percentile_cont(0.25) WITHIN GROUP (ORDER BY total_assets) AS p25,
 percentile_cont(0.50) WITHIN GROUP (ORDER BY total_assets) AS p50,
 percentile_cont(0.75) WITHIN GROUP (ORDER BY total_assets) AS p75,
 percentile_cont(0.95) WITHIN GROUP (ORDER BY total_assets) AS p95,
 max(total_assets) AS mx,
 percentile_cont(0.50) WITHIN GROUP (ORDER BY operating_revenue) AS rev_p50
FROM a;
