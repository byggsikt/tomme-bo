-- B5/00 Forprøver: organisasjonsform på alle konkursåpninger per år, og enhetssjekk i annual_account
\echo === orgform_per_aar ===
WITH a AS (SELECT orgnr, min(dato) AS opened FROM kunngjoring.insolvens
           WHERE type='Konkurs - åpning' AND dato >= DATE '2021-01-01' AND dato <= DATE '2026-08-24' GROUP BY 1)
SELECT extract(year FROM a.opened)::int AS aar,
       coalesce(nullif(trim(c.org_form_code),''),'<tom>') AS orgform,
       count(*) AS n
FROM a LEFT JOIN company_intel.company c USING (orgnr)
GROUP BY 1,2 ORDER BY 1, 3 DESC;
\echo === enhetssjekk_duplikater ===
SELECT a.fiscal_year, count(*) AS n_par,
       count(*) FILTER (WHERE a.total_assets = b.total_assets) AS like_verdier,
       count(*) FILTER (WHERE b.total_assets <> 0 AND abs(a.total_assets/nullif(b.total_assets,0) - 1) > 0.001) AS avvik,
       round(avg(a.total_assets/nullif(b.total_assets,0))::numeric,4) AS snitt_forhold
FROM company_intel.annual_account a
JOIN company_intel.annual_account b
  ON a.orgnr=b.orgnr AND a.fiscal_year=b.fiscal_year
 AND a.source_name='brreg-recovered' AND b.source_name='brreg-regnskap'
WHERE a.total_assets IS NOT NULL AND b.total_assets IS NOT NULL
GROUP BY 1 ORDER BY 1;
\echo === enhet_x_kilde_kohort ===
WITH o AS (SELECT orgnr, min(dato) AS opened FROM kunngjoring.insolvens
           WHERE type='Konkurs - åpning' AND dato BETWEEN '2023-09-01' AND '2024-12-31' GROUP BY 1)
SELECT coalesce(aa.amount_unit,'<NULL>') AS enhet, aa.source_name, aa.fiscal_year,
       count(*) AS n,
       percentile_disc(0.5) WITHIN GROUP (ORDER BY aa.total_assets) AS median_ta
FROM o JOIN company_intel.annual_account aa USING (orgnr)
WHERE aa.total_assets IS NOT NULL
GROUP BY 1,2,3 ORDER BY 3 DESC,4 DESC;
